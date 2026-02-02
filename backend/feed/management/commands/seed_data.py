from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

from feed.models import Post, Comment, PostLike, CommentLike


class Command(BaseCommand):
    help = 'Seeds the database with demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        
        # Create users
        users = []
        user_data = [
            ('alice', 'Alice Chen'),
            ('bob', 'Bob Smith'),
            ('charlie', 'Charlie Wilson'),
            ('diana', 'Diana Kumar'),
            ('ethan', 'Ethan Brown'),
            ('fiona', 'Fiona Garcia'),
            ('george', 'George Lee'),
            ('hannah', 'Hannah Davis'),
        ]
        
        for username, _ in user_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'password': 'password123'}
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
            
        self.stdout.write(f'Created {len(users)} users')
        
        # Create posts
        post_contents = [
            "Just finished building my first Django REST API! The serializers are a bit tricky at first but once you get the hang of them, they're super powerful. Anyone else have tips for handling nested relationships?",
            "Hot take: TypeScript is overrated for small projects. Sometimes plain JavaScript is just faster to ship. Change my mind! 🔥",
            "Anyone attending the PyCon next month? Would love to meetup with fellow Python enthusiasts!",
            "Finally cracked the N+1 query problem in our Django app. Turns out select_related and prefetch_related are your best friends. Our page load time went from 3s to 200ms!",
            "What's everyone's favorite VS Code extension? Mine is definitely GitLens - can't imagine working without it now.",
            "Just discovered htmx and it's changing how I think about frontend development. Less JavaScript, more hypermedia!",
            "Controversial opinion: We should write more tests. There, I said it. 🧪",
            "The new React 19 features look amazing! Can't wait to try out the new compiler.",
        ]
        
        posts = []
        for i, content in enumerate(post_contents):
            post = Post.objects.create(
                author=users[i % len(users)],
                content=content
            )
            posts.append(post)
            
        self.stdout.write(f'Created {len(posts)} posts')
        
        # Create nested comments
        comment_texts = [
            "Great point! I totally agree.",
            "Interesting perspective, but have you considered...",
            "This is exactly what I was looking for!",
            "Could you elaborate more on this?",
            "Respectfully disagree here. Here's why...",
            "Thanks for sharing this!",
            "This changed my mind completely.",
            "Adding to this - another tip is to use Django Debug Toolbar.",
            "Been there, done that. It's a journey!",
            "Bookmarked for later reference 📚",
        ]
        
        comments_created = 0
        for post in posts:
            # Add root level comments
            root_comments = []
            for _ in range(random.randint(2, 5)):
                comment = Comment.objects.create(
                    post=post,
                    author=random.choice(users),
                    content=random.choice(comment_texts)
                )
                root_comments.append(comment)
                comments_created += 1
            
            # Add nested replies
            for root_comment in root_comments:
                if random.random() > 0.5:
                    reply = Comment.objects.create(
                        post=post,
                        parent=root_comment,
                        author=random.choice(users),
                        content=random.choice(comment_texts)
                    )
                    comments_created += 1
                    
                    # Sometimes add deeper nesting
                    if random.random() > 0.6:
                        Comment.objects.create(
                            post=post,
                            parent=reply,
                            author=random.choice(users),
                            content=random.choice(comment_texts)
                        )
                        comments_created += 1
                        
        self.stdout.write(f'Created {comments_created} comments')
        
        # Create likes with timestamps within last 24 hours (for leaderboard)
        likes_created = 0
        now = timezone.now()
        
        for post in posts:
            # Random users like each post
            likers = random.sample(users, random.randint(1, len(users) - 1))
            for user in likers:
                if user != post.author:  # Can't like own post
                    try:
                        PostLike.objects.create(
                            post=post,
                            user=user,
                            # Spread likes across last 24 hours
                        )
                        # Manually set created_at within last 24h
                        like = PostLike.objects.filter(post=post, user=user).first()
                        like.created_at = now - timedelta(hours=random.randint(0, 23))
                        like.save()
                        likes_created += 1
                    except:
                        pass
        
        # Like some comments too
        all_comments = list(Comment.objects.all())
        for comment in all_comments:
            if random.random() > 0.3:
                likers = random.sample(users, random.randint(1, min(3, len(users))))
                for user in likers:
                    if user != comment.author:
                        try:
                            CommentLike.objects.create(
                                comment=comment,
                                user=user
                            )
                            like = CommentLike.objects.filter(comment=comment, user=user).first()
                            like.created_at = now - timedelta(hours=random.randint(0, 23))
                            like.save()
                            likes_created += 1
                        except:
                            pass
        
        self.stdout.write(f'Created {likes_created} likes')
        
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write('Demo users: alice, bob, charlie, diana, ethan, fiona, george, hannah')
        self.stdout.write('Password for all: password123')
