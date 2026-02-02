from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta


class Post(models.Model):
    """A text post in the community feed."""
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.author.username}: {self.content[:50]}"

class Comment(models.Model):
    """
    Threaded comment using Materialized Path pattern.
    
    The 'path' field stores the full ancestry path (e.g., "0001.0002.0003")
    which allows efficient querying of entire subtrees with a single query.
    This avoids the N+1 problem when loading nested comments.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Materialized path for efficient tree queries
    # Format: "0001.0002.0003" where each segment is zero-padded
    path = models.CharField(max_length=500, db_index=True)
    depth = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['path']  # Natural tree ordering
        indexes = [
            models.Index(fields=['post', 'path']),
        ]

    def __str__(self):
        return f"Comment by {self.author.username}: {self.content[:30]}"


    def save(self, *args, **kwargs):
        if not self.pk:  # New comment
            if self.parent:
                # Get sibling count under same parent
                sibling_count = Comment.objects.filter(
                    post=self.post,
                    parent=self.parent
                ).count()
                # Build path from parent's path
                self.path = f"{self.parent.path}.{sibling_count + 1:04d}"
                self.depth = self.parent.depth + 1
            else:
                # Root level comment
                root_count = Comment.objects.filter(
                    post=self.post,
                    parent__isnull=True
                ).count()
                self.path = f"{root_count + 1:04d}"
                self.depth = 0
        super().save(*args, **kwargs)


class PostLike(models.Model):
    """
    Like on a post. Awards 5 karma to the post author.
    Unique constraint prevents double-liking.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Database-level constraint to prevent double likes
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_post_like')
        ]

    def __str__(self):
        return f"{self.user.username} liked post {self.post.id}"


class CommentLike(models.Model):
    """
    Like on a comment. Awards 1 karma to the comment author.
    Unique constraint prevents double-liking.
    """
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Database-level constraint to prevent double likes
        constraints = [
            models.UniqueConstraint(fields=['comment', 'user'], name='unique_comment_like')
        ]

    def __str__(self):
        return f"{self.user.username} liked comment {self.comment.id}"


class LeaderboardManager:
    """
    Utility class to calculate the 24-hour rolling leaderboard.
    
    Karma is calculated dynamically from PostLike and CommentLike records,
    NOT stored as a simple integer field.
    """
    
    @staticmethod
    def get_top_users(limit=5):
        """
        Get top users by karma earned in the last 24 hours.
        
        The karma calculation:
        - 1 Like on a Post = 5 Karma (to the post author)
        - 1 Like on a Comment = 1 Karma (to the comment author)
        
        This uses a single optimized query with subqueries for aggregation.
        """
        cutoff = timezone.now() - timedelta(hours=24)
        
        # Subquery for post karma: count likes on user's posts * 5
        from django.db.models import OuterRef, Subquery
        
        post_karma_subquery = PostLike.objects.filter(
            post__author=OuterRef('pk'),
            created_at__gte=cutoff
        ).values('post__author').annotate(
            karma=Sum(models.Value(5))
        ).values('karma')[:1]
        
        comment_karma_subquery = CommentLike.objects.filter(
            comment__author=OuterRef('pk'),
            created_at__gte=cutoff
        ).values('comment__author').annotate(
            karma=Sum(models.Value(1))
        ).values('karma')[:1]
        
        # Combined query
        users = User.objects.annotate(
            post_karma=Coalesce(Subquery(post_karma_subquery), 0),
            comment_karma=Coalesce(Subquery(comment_karma_subquery), 0),
            total_karma=F('post_karma') + F('comment_karma')
        ).filter(
            total_karma__gt=0
        ).order_by('-total_karma')[:limit]
        
        return users
    
    @staticmethod
    def get_top_users_raw_sql(limit=5):
        """
        Alternative implementation using raw SQL for maximum efficiency.
        This is the actual query used in the API endpoint.
        """
        cutoff = timezone.now() - timedelta(hours=24)
        
        from django.db import connection
        
        query = """
        WITH post_karma AS (
            SELECT 
                p.author_id as user_id,
                COUNT(pl.id) * 5 as karma
            FROM feed_postlike pl
            JOIN feed_post p ON pl.post_id = p.id
            WHERE pl.created_at >= %s
            GROUP BY p.author_id
        ),
        comment_karma AS (
            SELECT 
                c.author_id as user_id,
                COUNT(cl.id) * 1 as karma
            FROM feed_commentlike cl
            JOIN feed_comment c ON cl.comment_id = c.id
            WHERE cl.created_at >= %s
            GROUP BY c.author_id
        ),
        total_karma AS (
            SELECT 
                COALESCE(pk.user_id, ck.user_id) as user_id,
                COALESCE(pk.karma, 0) + COALESCE(ck.karma, 0) as karma
            FROM post_karma pk
            FULL OUTER JOIN comment_karma ck ON pk.user_id = ck.user_id
        )
        SELECT 
            u.id,
            u.username,
            COALESCE(tk.karma, 0) as karma
        FROM auth_user u
        LEFT JOIN total_karma tk ON u.id = tk.user_id
        WHERE COALESCE(tk.karma, 0) > 0
        ORDER BY karma DESC
        LIMIT %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [cutoff, cutoff, limit])
            rows = cursor.fetchall()
            
        return [
            {'id': row[0], 'username': row[1], 'karma': row[2]}
            for row in rows
        ]
