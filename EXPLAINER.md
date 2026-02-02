# EXPLAINER.md - Technical Deep Dive

## 1. The Tree: Nested Comment Model

### Database Design

I use the **Materialized Path** pattern to model nested comments. Each comment stores its full ancestry path as a string:

```python
class Comment(models.Model):
    post = models.ForeignKey(Post, ...)
    parent = models.ForeignKey('self', null=True, ...)
    content = models.TextField()
    
    # Materialized path for efficient tree queries
    path = models.CharField(max_length=500, db_index=True)
    depth = models.PositiveIntegerField(default=0)
```

**Path Format Examples:**
- Root comment: `"0001"`
- First reply to root: `"0001.0001"`
- Second reply to that: `"0001.0001.0001"`
- Second root comment: `"0002"`

### Why Materialized Path?

| Approach | Load Tree | Insert | Move Node |
|----------|-----------|--------|-----------|
| Adjacency List | O(n) queries | O(1) | O(1) |
| Nested Sets | O(1) query | O(n) | O(n) |
| **Materialized Path** | **O(1) query** | **O(1)** | O(subtree) |

For a discussion forum where reads vastly outnumber writes, and node moves are rare, materialized path is optimal.

### Serialization Without N+1

The key insight: **fetch all comments in ONE query, build tree in Python**.

```python
# In PostDetailSerializer.get_comments():

# 1. Single query: get ALL comments for the post (ordered by path)
comments = obj.comments.select_related('author').order_by('path')

# 2. Build lookup table
comment_dict = {}
root_comments = []

for comment in comments:
    comment_data = serialize(comment)
    comment_dict[comment.id] = comment_data
    
    if comment.parent_id is None:
        root_comments.append(comment_data)
    else:
        # O(1) lookup - parent is guaranteed to exist (ordered by path)
        comment_dict[comment.parent_id]['replies'].append(comment_data)

return root_comments
```

**Query Count**: Always 2-3 queries regardless of comment depth:
1. Fetch comments with authors (`select_related`)
2. Fetch user's liked comments (for `is_liked` flag)
3. Optional: count aggregation

**Memory**: O(n) where n = total comments - we hold all comments in memory during serialization.

---

## 2. The Math: 24-Hour Leaderboard Query

### The Challenge

Calculate karma earned in the last 24 hours where:
- Post like = 5 karma (to post author)
- Comment like = 1 karma (to comment author)

**Constraint**: Must be calculated dynamically from Like records, not stored in a User.karma field.

### The Query (ORM version used in production)

```python
def get(self, request):
    cutoff = timezone.now() - timedelta(hours=24)
    
    # Post karma: count likes on user's posts * 5
    post_karma = (
        PostLike.objects
        .filter(created_at__gte=cutoff)
        .values('post__author')
        .annotate(karma=Count('id') * 5)
    )
    
    # Comment karma: count likes on user's comments * 1
    comment_karma = (
        CommentLike.objects
        .filter(created_at__gte=cutoff)
        .values('comment__author')
        .annotate(karma=Count('id'))
    )
    
    # Combine in Python (efficient for small result sets)
    karma_by_user = {}
    for item in post_karma:
        user_id = item['post__author']
        karma_by_user[user_id] = karma_by_user.get(user_id, 0) + item['karma']
    
    for item in comment_karma:
        user_id = item['comment__author']
        karma_by_user[user_id] = karma_by_user.get(user_id, 0) + item['karma']
    
    # Sort and take top 5
    sorted_users = sorted(karma_by_user.items(), key=lambda x: x[1], reverse=True)[:5]
```

### Equivalent Raw SQL (for reference)

```sql
WITH post_karma AS (
    SELECT 
        p.author_id as user_id,
        COUNT(pl.id) * 5 as karma
    FROM feed_postlike pl
    JOIN feed_post p ON pl.post_id = p.id
    WHERE pl.created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY p.author_id
),
comment_karma AS (
    SELECT 
        c.author_id as user_id,
        COUNT(cl.id) * 1 as karma
    FROM feed_commentlike cl
    JOIN feed_comment c ON cl.comment_id = c.id
    WHERE cl.created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY c.author_id
)
SELECT 
    u.id,
    u.username,
    COALESCE(pk.karma, 0) + COALESCE(ck.karma, 0) as total_karma
FROM auth_user u
LEFT JOIN post_karma pk ON u.id = pk.user_id
LEFT JOIN comment_karma ck ON u.id = ck.user_id
WHERE COALESCE(pk.karma, 0) + COALESCE(ck.karma, 0) > 0
ORDER BY total_karma DESC
LIMIT 5;
```

### Performance Characteristics

- **Indexes**: `created_at` on both Like tables is critical
- **Query Complexity**: O(n) where n = likes in last 24h
- **For scale**: Consider materialized view refreshed every minute, or Redis cache

---

## 3. The AI Audit: Catching AI Mistakes

### Bug #1: Subquery Aggregation Error

**What AI Wrote (Initial):**
```python
post_karma_subquery = PostLike.objects.filter(
    post__author=OuterRef('pk'),
    created_at__gte=cutoff
).values('post__author').annotate(
    karma=Sum(models.Value(5))  # BUG: Sum of constant
).values('karma')[:1]
```

**The Problem:** `Sum(Value(5))` doesn't multiply count by 5 - it tries to sum the literal value 5, which is always 5 regardless of row count.

**My Fix:**
```python
# Use Count * 5 instead of Sum(Value(5))
post_karma = (
    PostLike.objects
    .filter(created_at__gte=cutoff)
    .values('post__author')
    .annotate(karma=Count('id') * 5)  # FIXED: Count * multiplier
)
```

### Bug #2: FULL OUTER JOIN in SQLite

**What AI Wrote:**
```sql
SELECT ... FROM post_karma pk
FULL OUTER JOIN comment_karma ck ON pk.user_id = ck.user_id
```

**The Problem:** SQLite doesn't support `FULL OUTER JOIN`. This would crash on our default database.

**My Fix:** Moved to Python-based combination which works on any database:
```python
karma_by_user = {}
for item in post_karma:
    karma_by_user[user_id] = karma_by_user.get(user_id, 0) + item['karma']
for item in comment_karma:
    karma_by_user[user_id] = karma_by_user.get(user_id, 0) + item['karma']
```

### Bug #3: N+1 in Comment Serialization

**What AI Initially Suggested:**
```python
class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    
    def get_replies(self, obj):
        # BUG: This queries DB for EACH comment!
        return CommentSerializer(
            obj.replies.all(),  # N+1 query here
            many=True,
            context=self.context
        ).data
```

**The Problem:** With 50 comments, this fires 50+ queries. Classic N+1.

**My Fix:** Pre-fetch all comments, build tree in memory:
```python
# Fetch ONCE, build tree in Python
comments = obj.comments.select_related('author').order_by('path')
comment_dict = {c.id: serialize(c) for c in comments}

for comment in comments:
    if comment.parent_id:
        comment_dict[comment.parent_id]['replies'].append(comment_dict[comment.id])
```

---

## 4. Concurrency: Preventing Double Likes

### The Race Condition

```
Time    User A              User B
----    ------              ------
T1      Check: not liked    
T2                          Check: not liked
T3      Insert like         
T4                          Insert like  ← DUPLICATE!
```

### Solution: Database Constraints

```python
class PostLike(models.Model):
    post = models.ForeignKey(Post, ...)
    user = models.ForeignKey(User, ...)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user'], 
                name='unique_post_like'
            )
        ]
```

### Handling in Views

```python
@action(detail=True, methods=['post'])
def like(self, request, pk=None):
    post = self.get_object()
    
    try:
        with transaction.atomic():
            PostLike.objects.create(post=post, user=request.user)
            return Response({'status': 'liked'})
    except IntegrityError:
        # Constraint violation = already liked
        return Response({'error': 'Already liked'}, status=400)
```

**Why This Works:**
1. The `UNIQUE` constraint is enforced at database level
2. Even if two requests pass Python checks simultaneously, only one INSERT succeeds
3. The other gets `IntegrityError` which we handle gracefully

---

## Summary

| Challenge | Solution |
|-----------|----------|
| N+1 queries for comments | Materialized path + single query + Python tree building |
| 24h dynamic karma | Aggregation query on Like tables filtered by timestamp |
| Race conditions on likes | Database UNIQUE constraint + IntegrityError handling |
| AI bugs | Manual review, testing, understanding query behavior |

The key philosophy: **Trust the database for data integrity, use application code for business logic.**
