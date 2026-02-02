from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, PostLike, CommentLike


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class CommentSerializer(serializers.ModelSerializer):
    """
    Flat comment serializer - used for individual comment operations.
    """
    author = UserSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'parent', 'content', 
            'created_at', 'depth', 'path', 'like_count', 'is_liked', 'replies'
        ]
        read_only_fields = ['author', 'depth', 'path']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Use prefetched data if available
            if hasattr(obj, '_user_liked'):
                return obj._user_liked
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_replies(self, obj):
        # This will be populated by the view for tree structure
        return []


class CommentTreeSerializer(serializers.Serializer):
    """
    Serializer for building comment trees efficiently.
    
    This serializer works with pre-fetched flat comment lists
    and builds the tree structure in Python, avoiding N+1 queries.
    """
    id = serializers.IntegerField()
    author = UserSerializer()
    content = serializers.CharField()
    created_at = serializers.DateTimeField()
    depth = serializers.IntegerField()
    path = serializers.CharField()
    like_count = serializers.IntegerField()
    is_liked = serializers.BooleanField()
    replies = serializers.ListField(child=serializers.DictField(), default=list)


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'content', 'created_at', 
            'like_count', 'comment_count', 'is_liked'
        ]
        read_only_fields = ['author']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Use prefetched data if available
            if hasattr(obj, '_user_liked'):
                return obj._user_liked
            return obj.likes.filter(user=request.user).exists()
        return False


class PostDetailSerializer(PostSerializer):
    """
    Post serializer with nested comment tree.
    """
    comments = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ['comments']

    def get_comments(self, obj):
        """
        Build comment tree from flat prefetched queryset.
        
        Algorithm:
        1. Get all comments for the post in a single query (ordered by path)
        2. Build tree structure in Python using a dictionary lookup
        3. Return only root-level comments with nested replies
        
        This avoids the N+1 problem - we make exactly 1 query for all comments
        regardless of nesting depth.
        """
        request = self.context.get('request')
        user = request.user if request else None
        
        # Single query: get all comments with their authors, ordered by path
        comments = obj.comments.select_related('author').prefetch_related('likes').order_by('path')
        
        # Annotate with like counts efficiently
        comment_list = list(comments)
        
        # Build lookup table and mark user likes
        user_liked_comments = set()
        if user and user.is_authenticated:
            user_liked_comments = set(
                CommentLike.objects.filter(
                    comment__post=obj,
                    user=user
                ).values_list('comment_id', flat=True)
            )
        
        # Build tree structure
        comment_dict = {}
        root_comments = []
        
        for comment in comment_list:
            comment_data = {
                'id': comment.id,
                'author': {'id': comment.author.id, 'username': comment.author.username},
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'depth': comment.depth,
                'path': comment.path,
                'like_count': comment.likes.count(),
                'is_liked': comment.id in user_liked_comments,
                'replies': []
            }
            comment_dict[comment.id] = comment_data
            
            if comment.parent_id is None:
                root_comments.append(comment_data)
            else:
                # Add to parent's replies
                parent_data = comment_dict.get(comment.parent_id)
                if parent_data:
                    parent_data['replies'].append(comment_data)
        
        return root_comments


class PostLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLike
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['user']


class CommentLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentLike
        fields = ['id', 'comment', 'user', 'created_at']
        read_only_fields = ['user']


class LeaderboardUserSerializer(serializers.Serializer):
    """Serializer for leaderboard entries."""
    id = serializers.IntegerField()
    username = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.IntegerField(required=False)


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments."""
    class Meta:
        model = Comment
        fields = ['id', 'post', 'parent', 'content']

    def validate(self, data):
        # Ensure parent comment belongs to the same post
        if data.get('parent'):
            if data['parent'].post_id != data['post'].id:
                raise serializers.ValidationError(
                    "Parent comment must belong to the same post"
                )
        return data
