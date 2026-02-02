import { useState, useEffect } from 'react';
import { getPosts, createPost } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Post from './Post';

export default function Feed() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newPostContent, setNewPostContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchPosts = async (pageNum = 1, append = false) => {
    try {
      const data = await getPosts(pageNum);
      if (append) {
        setPosts(prev => [...prev, ...data.results]);
      } else {
        setPosts(data.results || []);
      }
      setHasMore(!!data.next);
    } catch (err) {
      console.error('Failed to fetch posts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!newPostContent.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const newPost = await createPost(newPostContent.trim());
      setPosts(prev => [{ ...newPost, is_liked: false }, ...prev]);
      setNewPostContent('');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const loadMore = () => {
    if (hasMore && !loading) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchPosts(nextPage, true);
    }
  };

  if (loading && posts.length === 0) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-slate-900/50 rounded-2xl p-5 animate-pulse">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-slate-700"></div>
              <div className="space-y-2">
                <div className="h-4 w-24 bg-slate-700 rounded"></div>
                <div className="h-3 w-16 bg-slate-700 rounded"></div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-4 w-full bg-slate-700 rounded"></div>
              <div className="h-4 w-3/4 bg-slate-700 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Create Post Form */}
      {user && (
        <form 
          onSubmit={handleCreatePost}
          className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800 p-5"
        >
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold flex-shrink-0">
              {user.username[0].toUpperCase()}
            </div>
            <div className="flex-1">
              <textarea
                value={newPostContent}
                onChange={(e) => setNewPostContent(e.target.value)}
                placeholder="What's on your mind?"
                className="w-full bg-slate-800/50 text-slate-200 rounded-xl p-4 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none placeholder-slate-500"
                rows={3}
              />
              {error && (
                <p className="text-red-400 text-sm mt-2">{error}</p>
              )}
              <div className="flex justify-end mt-3">
                <button
                  type="submit"
                  disabled={isSubmitting || !newPostContent.trim()}
                  className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-medium rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
                >
                  {isSubmitting ? 'Posting...' : 'Post'}
                </button>
              </div>
            </div>
          </div>
        </form>
      )}

      {/* Posts List */}
      <div className="space-y-4">
        {posts.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-slate-400 text-lg">No posts yet!</p>
            <p className="text-slate-500 mt-2">Be the first to share something.</p>
          </div>
        ) : (
          posts.map(post => (
            <Post key={post.id} post={post} />
          ))
        )}
      </div>

      {/* Load More */}
      {hasMore && posts.length > 0 && (
        <div className="text-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
}
