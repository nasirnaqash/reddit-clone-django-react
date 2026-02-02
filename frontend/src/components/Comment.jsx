import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { likeComment, unlikeComment, createComment } from '../services/api';

function CommentItem({ comment, postId, onCommentAdded, depth = 0 }) {
  const { user } = useAuth();
  const [isLiked, setIsLiked] = useState(comment.is_liked);
  const [likeCount, setLikeCount] = useState(comment.like_count);
  const [isReplying, setIsReplying] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleLike = async () => {
    if (!user) return;
    
    try {
      if (isLiked) {
        await unlikeComment(comment.id);
        setLikeCount(c => c - 1);
      } else {
        await likeComment(comment.id);
        setLikeCount(c => c + 1);
      }
      setIsLiked(!isLiked);
    } catch (err) {
      console.error('Failed to toggle like:', err);
    }
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyContent.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const newComment = await createComment(postId, replyContent.trim(), comment.id);
      setReplyContent('');
      setIsReplying(false);
      if (onCommentAdded) {
        onCommentAdded(newComment);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
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
    <div className={`${depth > 0 ? 'border-l-2 border-slate-700 pl-4 ml-4' : ''}`}>
      <div className="py-3">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            {comment.author.username[0].toUpperCase()}
          </div>

          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-slate-200">{comment.author.username}</span>
              <span className="text-slate-500 text-sm">·</span>
              <span className="text-slate-500 text-sm">{timeAgo(comment.created_at)}</span>
            </div>

            {/* Content */}
            <p className="text-slate-300 break-words">{comment.content}</p>

            {/* Actions */}
            <div className="flex items-center gap-4 mt-2">
              <button
                onClick={handleLike}
                disabled={!user}
                className={`flex items-center gap-1 text-sm transition-colors ${
                  isLiked 
                    ? 'text-pink-400 hover:text-pink-300' 
                    : 'text-slate-500 hover:text-pink-400'
                } ${!user && 'cursor-not-allowed opacity-50'}`}
              >
                <svg 
                  className="w-4 h-4" 
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
                <span>{likeCount}</span>
              </button>

              {user && depth < 5 && (
                <button
                  onClick={() => setIsReplying(!isReplying)}
                  className="text-sm text-slate-500 hover:text-blue-400 transition-colors"
                >
                  Reply
                </button>
              )}
            </div>

            {/* Reply form */}
            {isReplying && (
              <form onSubmit={handleReply} className="mt-3">
                <textarea
                  value={replyContent}
                  onChange={(e) => setReplyContent(e.target.value)}
                  placeholder={`Reply to ${comment.author.username}...`}
                  className="w-full bg-slate-800 text-slate-200 rounded-lg p-3 text-sm border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
                  rows={2}
                />
                {error && <p className="text-red-400 text-sm mt-1">{error}</p>}
                <div className="flex gap-2 mt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting || !replyContent.trim()}
                    className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? 'Posting...' : 'Reply'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsReplying(false);
                      setReplyContent('');
                    }}
                    className="px-3 py-1 text-slate-400 hover:text-slate-200 text-sm transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>

      {/* Nested replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="space-y-0">
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              postId={postId}
              onCommentAdded={onCommentAdded}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CommentList({ comments, postId, onCommentAdded }) {
  if (!comments || comments.length === 0) {
    return (
      <p className="text-slate-500 text-center py-4">
        No comments yet. Be the first to comment!
      </p>
    );
  }

  return (
    <div className="space-y-1 divide-y divide-slate-800">
      {comments.map((comment) => (
        <CommentItem
          key={comment.id}
          comment={comment}
          postId={postId}
          onCommentAdded={onCommentAdded}
          depth={0}
        />
      ))}
    </div>
  );
}
