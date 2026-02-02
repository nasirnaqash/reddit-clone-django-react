import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { likePost, unlikePost, getPost, createComment } from '../services/api';
import CommentList from './Comment';

export default function Post({ post: initialPost }) {
  const { user } = useAuth();
  const [post, setPost] = useState(initialPost);
  const [isLiked, setIsLiked] = useState(initialPost.is_liked);
  const [likeCount, setLikeCount] = useState(initialPost.like_count);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [error, setError] = useState(null);

  const handleLike = async () => {
    if (!user) return;
    
    try {
      if (isLiked) {
        await unlikePost(post.id);
        setLikeCount(c => c - 1);
      } else {
        await likePost(post.id);
        setLikeCount(c => c + 1);
      }
      setIsLiked(!isLiked);
    } catch (err) {
      console.error('Failed to toggle like:', err);
    }
  };

  const loadComments = async () => {
    if (showComments) {
      setShowComments(false);
      return;
    }

    setLoadingComments(true);
    try {
      const fullPost = await getPost(post.id);
      setComments(fullPost.comments || []);
      setShowComments(true);
    } catch (err) {
      console.error('Failed to load comments:', err);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleSubmitComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim() || isSubmittingComment) return;

    setIsSubmittingComment(true);
    setError(null);

    try {
      await createComment(post.id, newComment.trim());
      setNewComment('');
      // Reload comments to show the new one
      const fullPost = await getPost(post.id);
      setComments(fullPost.comments || []);
      setPost(prev => ({ ...prev, comment_count: fullPost.comment_count }));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleCommentAdded = async () => {
    // Reload comments when a nested reply is added
    const fullPost = await getPost(post.id);
    setComments(fullPost.comments || []);
    setPost(prev => ({ ...prev, comment_count: fullPost.comment_count }));
  };

  const timeAgo = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <article className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800 overflow-hidden transition-all hover:border-slate-700">
      {/* Post Header */}
      <div className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
            {post.author.username[0].toUpperCase()}
          </div>
          <div>
            <h3 className="font-medium text-slate-100">{post.author.username}</h3>
            <p className="text-sm text-slate-500">{timeAgo(post.created_at)}</p>
          </div>
        </div>

        {/* Post Content */}
        <p className="text-slate-200 leading-relaxed whitespace-pre-wrap">{post.content}</p>
      </div>

      {/* Post Actions */}
      <div className="px-5 py-3 border-t border-slate-800 flex items-center gap-6">
        <button
          onClick={handleLike}
          disabled={!user}
          className={`flex items-center gap-2 transition-all duration-200 ${
            isLiked 
              ? 'text-pink-400 hover:text-pink-300' 
              : 'text-slate-500 hover:text-pink-400'
          } ${!user && 'cursor-not-allowed opacity-50'}`}
        >
          <svg 
            className={`w-5 h-5 transition-transform ${isLiked ? 'scale-110' : ''}`}
            fill={isLiked ? 'currentColor' : 'none'} 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" 
            />
          </svg>
          <span className="font-medium">{likeCount}</span>
          <span className="text-xs text-slate-500">(+5 karma)</span>
        </button>

        <button
          onClick={loadComments}
          className="flex items-center gap-2 text-slate-500 hover:text-blue-400 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" 
            />
          </svg>
          <span className="font-medium">{post.comment_count}</span>
          {loadingComments && <span className="text-xs">(loading...)</span>}
        </button>
      </div>

      {/* Comments Section */}
      {showComments && (
        <div className="border-t border-slate-800">
          {/* New Comment Form */}
          {user && (
            <form onSubmit={handleSubmitComment} className="p-4 border-b border-slate-800">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                  {user.username[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <textarea
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Write a comment..."
                    className="w-full bg-slate-800 text-slate-200 rounded-lg p-3 text-sm border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
                    rows={2}
                  />
                  {error && <p className="text-red-400 text-sm mt-1">{error}</p>}
                  <div className="flex justify-end mt-2">
                    <button
                      type="submit"
                      disabled={isSubmittingComment || !newComment.trim()}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSubmittingComment ? 'Posting...' : 'Comment'}
                    </button>
                  </div>
                </div>
              </div>
            </form>
          )}

          {/* Comments List */}
          <div className="p-4">
            <CommentList 
              comments={comments} 
              postId={post.id} 
              onCommentAdded={handleCommentAdded}
            />
          </div>
        </div>
      )}
    </article>
  );
}
