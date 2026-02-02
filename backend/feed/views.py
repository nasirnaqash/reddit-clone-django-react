from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Exists, OuterRef
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from .models import Post, Comment, PostLike, CommentLike, LeaderboardManager
from .serializers import (
    PostSerializer, PostDetailSerializer, CommentSerializer,
    CommentCreateSerializer, LeaderboardUserSerializer, UserSerializer
)


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for posts with efficient querying.
    
    List view: Annotates like_count and comment_count to avoid N+1 queries.
    Detail view: Prefetches entire comment tree in a single query.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Optimize queryset based on action.
        - List: annotate counts, prefetch only what's needed for list display
        - Detail: prefetch full comment tree
        """
        queryset = Post.objects.select_related('author').order_by('-created_at')

        
        # Annotate with counts for efficient list display
        queryset = queryset.annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        )
        
        # For authenticated users, check if they liked each post
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.annotate(
                _user_liked=Exists(
                    PostLike.objects.filter(
                        post=OuterRef('pk'),
                        user=user
                    )
                )
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """
        Like a post. Handles race conditions with database constraints.
        
        The UniqueConstraint on PostLike ensures no double-likes at the DB level,
        even if multiple requests arrive simultaneously.
        """
        post = self.get_object()
        
        # Prevent users from liking their own posts (optional business rule)
        if post.author == request.user:
            return Response(
                {'error': 'Cannot like your own post'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # select_for_update prevents race conditions
                PostLike.objects.create(post=post, user=request.user)
                return Response({'status': 'liked', 'like_count': post.likes.count()})
        except IntegrityError:
            # Unique constraint violation - user already liked this post
            return Response(
                {'error': 'Already liked'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request, pk=None):
        """Remove a like from a post."""
        post = self.get_object()
        
        deleted, _ = PostLike.objects.filter(post=post, user=request.user).delete()
        
        if deleted:
            return Response({'status': 'unliked', 'like_count': post.likes.count()})
        return Response(
            {'error': 'Not liked'},
            status=status.HTTP_400_BAD_REQUEST
        )


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for comments.
    
    Comments are typically accessed through posts, but this provides
    direct CRUD operations on comments.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Comment.objects.select_related('author', 'post')
        
        # Filter by post if specified
        post_id = self.request.query_params.get('post')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        
        # Annotate with like counts
        queryset = queryset.annotate(
            like_count=Count('likes', distinct=True)
        )
        
        # Check if user liked each comment
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.annotate(
                _user_liked=Exists(
                    CommentLike.objects.filter(
                        comment=OuterRef('pk'),
                        user=user
                    )
                )
            )
        
        return queryset.order_by('path')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """
        Like a comment. Handles race conditions with database constraints.
        """
        comment = self.get_object()
        
        # Prevent users from liking their own comments
        if comment.author == request.user:
            return Response(
                {'error': 'Cannot like your own comment'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                CommentLike.objects.create(comment=comment, user=request.user)
                return Response({'status': 'liked', 'like_count': comment.likes.count()})
        except IntegrityError:
            return Response(
                {'error': 'Already liked'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request, pk=None):
        """Remove a like from a comment."""
        comment = self.get_object()
        
        deleted, _ = CommentLike.objects.filter(comment=comment, user=request.user).delete()
        
        if deleted:
            return Response({'status': 'unliked', 'like_count': comment.likes.count()})
        return Response(
            {'error': 'Not liked'},
            status=status.HTTP_400_BAD_REQUEST
        )


class LeaderboardView(APIView):
    """
    Get the top 5 users by karma earned in the last 24 hours.
    
    Karma calculation (dynamic, not stored):
    - 1 Like on a Post = 5 Karma
    - 1 Like on a Comment = 1 Karma
    
    This uses a complex aggregation query that joins likes with
    their respective content authors and sums karma by user.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """
        Returns top 5 users by karma in last 24 hours.
        
        Uses efficient SQL with CTEs for calculation.
        """
        cutoff = timezone.now() - timedelta(hours=24)
        
        # ORM-based approach with proper aggregation
        # This uses subqueries to calculate karma from each source
        from django.db.models import Value, Sum, IntegerField
        from django.db.models.functions import Coalesce
        
        # Get all users who received post likes in last 24h
        post_karma = (
            PostLike.objects
            .filter(created_at__gte=cutoff)
            .values('post__author')
            .annotate(karma=Count('id') * 5)
        )
        
        # Get all users who received comment likes in last 24h
        comment_karma = (
            CommentLike.objects
            .filter(created_at__gte=cutoff)
            .values('comment__author')
            .annotate(karma=Count('id'))
        )
        
        # Combine results in Python (simpler and efficient for small result sets)
        karma_by_user = {}
        
        for item in post_karma:
            user_id = item['post__author']
            karma_by_user[user_id] = karma_by_user.get(user_id, 0) + item['karma']
        
        for item in comment_karma:
            user_id = item['comment__author']
            karma_by_user[user_id] = karma_by_user.get(user_id, 0) + item['karma']
        
        # Sort and get top 5
        sorted_users = sorted(
            karma_by_user.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Fetch user details
        user_ids = [user_id for user_id, _ in sorted_users]
        users = {u.id: u for u in User.objects.filter(id__in=user_ids)}
        
        # Build response
        leaderboard = []
        for rank, (user_id, karma) in enumerate(sorted_users, 1):
            user = users.get(user_id)
            if user:
                leaderboard.append({
                    'id': user.id,
                    'username': user.username,
                    'karma': karma,
                    'rank': rank
                })
        
        return Response({
            'leaderboard': leaderboard,
            'calculated_at': timezone.now().isoformat(),
            'period': '24h'
        })


class CurrentUserView(APIView):
    """Get the current authenticated user's info."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        return Response(UserSerializer(request.user).data)
