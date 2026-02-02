from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Post, Comment, PostLike, CommentLike


class LeaderboardTestCase(APITestCase):
    """
    Test the 24-hour rolling leaderboard calculation.
    
    This is the most complex aggregation in the app and needs
    thorough testing to ensure karma is calculated correctly.
    """
    
    def setUp(self):
        """Create test users and content."""
        self.user1 = User.objects.create_user('user1', password='test123')
        self.user2 = User.objects.create_user('user2', password='test123')
        self.user3 = User.objects.create_user('user3', password='test123')
        self.user4 = User.objects.create_user('user4', password='test123')
        
        # Create posts
        self.post1 = Post.objects.create(author=self.user1, content='Post 1')
        self.post2 = Post.objects.create(author=self.user2, content='Post 2')
        
        # Create comments
        self.comment1 = Comment.objects.create(
            post=self.post1, 
            author=self.user1, 
            content='Comment 1'
        )
        self.comment2 = Comment.objects.create(
            post=self.post1, 
            author=self.user2, 
            content='Comment 2'
        )
    
    def test_post_like_gives_5_karma(self):
        """Liking a post should give the author 5 karma."""
        # user2 likes user1's post
        PostLike.objects.create(post=self.post1, user=self.user2)
        
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        leaderboard = response.data['leaderboard']
        
        # user1 should have 5 karma from post like
        user1_entry = next((u for u in leaderboard if u['username'] == 'user1'), None)
        self.assertIsNotNone(user1_entry)
        self.assertEqual(user1_entry['karma'], 5)
    
    def test_comment_like_gives_1_karma(self):
        """Liking a comment should give the author 1 karma."""
        # user3 likes user1's comment
        CommentLike.objects.create(comment=self.comment1, user=self.user3)
        
        response = self.client.get('/api/leaderboard/')
        leaderboard = response.data['leaderboard']
        
        # user1 should have 1 karma from comment like
        user1_entry = next((u for u in leaderboard if u['username'] == 'user1'), None)
        self.assertIsNotNone(user1_entry)
        self.assertEqual(user1_entry['karma'], 1)
    
    def test_combined_karma_calculation(self):
        """Test that post and comment karma are summed correctly."""
        # user3 likes user1's post (5 karma)
        PostLike.objects.create(post=self.post1, user=self.user3)
        # user4 likes user1's post (5 more karma)
        PostLike.objects.create(post=self.post1, user=self.user4)
        # user2 likes user1's comment (1 karma)
        CommentLike.objects.create(comment=self.comment1, user=self.user2)
        
        response = self.client.get('/api/leaderboard/')
        leaderboard = response.data['leaderboard']
        
        # user1 should have 11 karma total (5+5+1)
        user1_entry = next((u for u in leaderboard if u['username'] == 'user1'), None)
        self.assertIsNotNone(user1_entry)
        self.assertEqual(user1_entry['karma'], 11)
    
    def test_only_counts_last_24_hours(self):
        """Karma from likes older than 24 hours should not count."""
        # Create a like and backdate it to 25 hours ago
        like = PostLike.objects.create(post=self.post1, user=self.user2)
        like.created_at = timezone.now() - timedelta(hours=25)
        like.save()
        
        response = self.client.get('/api/leaderboard/')
        leaderboard = response.data['leaderboard']
        
        # user1 should NOT appear (old like doesn't count)
        user1_entry = next((u for u in leaderboard if u['username'] == 'user1'), None)
        self.assertIsNone(user1_entry)
    
    def test_leaderboard_ordering(self):
        """Users should be ranked by karma descending."""
        # Give user1: 10 karma (2 post likes)
        PostLike.objects.create(post=self.post1, user=self.user2)
        PostLike.objects.create(post=self.post1, user=self.user3)
        
        # Give user2: 5 karma (1 post like)
        PostLike.objects.create(post=self.post2, user=self.user1)
        
        response = self.client.get('/api/leaderboard/')
        leaderboard = response.data['leaderboard']
        
        # user1 should be first with 10 karma
        self.assertEqual(leaderboard[0]['username'], 'user1')
        self.assertEqual(leaderboard[0]['karma'], 10)
        
        # user2 should be second with 5 karma
        self.assertEqual(leaderboard[1]['username'], 'user2')
        self.assertEqual(leaderboard[1]['karma'], 5)
    
    def test_top_5_limit(self):
        """Leaderboard should only return top 5 users."""
        # Create 7 more users
        extra_users = [
            User.objects.create_user(f'extra{i}', password='test123')
            for i in range(7)
        ]
        
        # Create posts for each and give them likes
        all_users = [self.user1, self.user2, self.user3, self.user4] + extra_users
        posts = []
        for user in all_users:
            post = Post.objects.create(author=user, content=f'Post by {user.username}')
            posts.append(post)
        
        # Give each user different amounts of karma
        for i, post in enumerate(posts):
            # Each subsequent user gets more likes
            for j in range(i + 1):
                if all_users[j] != post.author:
                    try:
                        PostLike.objects.create(post=post, user=all_users[j])
                    except:
                        pass
        
        response = self.client.get('/api/leaderboard/')
        leaderboard = response.data['leaderboard']
        
        # Should only return 5 users max
        self.assertLessEqual(len(leaderboard), 5)


class ConcurrencyTestCase(APITestCase):
    """Test double-like prevention and race condition handling."""
    
    def setUp(self):
        self.user1 = User.objects.create_user('user1', password='test123')
        self.user2 = User.objects.create_user('user2', password='test123')
        self.post = Post.objects.create(author=self.user1, content='Test post')
        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user1,
            content='Test comment'
        )
    
    def test_cannot_double_like_post(self):
        """Users cannot like the same post twice."""
        self.client.force_authenticate(user=self.user2)
        
        # First like should succeed
        response = self.client.post(f'/api/posts/{self.post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Second like should fail
        response = self.client.post(f'/api/posts/{self.post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Already liked', response.data['error'])
        
        # Should still only have 1 like
        self.assertEqual(self.post.likes.count(), 1)
    
    def test_cannot_double_like_comment(self):
        """Users cannot like the same comment twice."""
        self.client.force_authenticate(user=self.user2)
        
        # First like should succeed
        response = self.client.post(f'/api/comments/{self.comment.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Second like should fail
        response = self.client.post(f'/api/comments/{self.comment.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Should still only have 1 like
        self.assertEqual(self.comment.likes.count(), 1)
    
    def test_cannot_like_own_post(self):
        """Users cannot like their own posts."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(f'/api/posts/{self.post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('own post', response.data['error'])
    
    def test_cannot_like_own_comment(self):
        """Users cannot like their own comments."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(f'/api/comments/{self.comment.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CommentTreeTestCase(TestCase):
    """Test nested comment tree structure."""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='test123')
        self.post = Post.objects.create(author=self.user, content='Test post')
    
    def test_root_comment_path(self):
        """Root comments should have simple paths."""
        comment1 = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='First root comment'
        )
        comment2 = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='Second root comment'
        )
        
        self.assertEqual(comment1.path, '0001')
        self.assertEqual(comment1.depth, 0)
        self.assertEqual(comment2.path, '0002')
        self.assertEqual(comment2.depth, 0)
    
    def test_nested_comment_path(self):
        """Nested comments should have parent path as prefix."""
        root = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='Root comment'
        )
        reply = Comment.objects.create(
            post=self.post,
            parent=root,
            author=self.user,
            content='Reply'
        )
        deep_reply = Comment.objects.create(
            post=self.post,
            parent=reply,
            author=self.user,
            content='Deep reply'
        )
        
        self.assertEqual(reply.path, '0001.0001')
        self.assertEqual(reply.depth, 1)
        self.assertEqual(deep_reply.path, '0001.0001.0001')
        self.assertEqual(deep_reply.depth, 2)
    
    def test_comment_ordering_by_path(self):
        """Comments should be ordered correctly by path."""
        root1 = Comment.objects.create(
            post=self.post, author=self.user, content='Root 1'
        )
        root2 = Comment.objects.create(
            post=self.post, author=self.user, content='Root 2'
        )
        reply1 = Comment.objects.create(
            post=self.post, parent=root1, author=self.user, content='Reply to 1'
        )
        
        comments = list(Comment.objects.filter(post=self.post).order_by('path'))
        
        # Should be: root1, reply1, root2
        self.assertEqual(comments[0], root1)
        self.assertEqual(comments[1], reply1)
        self.assertEqual(comments[2], root2)
