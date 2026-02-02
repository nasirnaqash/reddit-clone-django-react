import { useState, useEffect } from 'react';
import { getLeaderboard } from '../services/api';

const MEDAL_COLORS = {
  1: 'from-amber-400 to-yellow-500',
  2: 'from-slate-300 to-slate-400',
  3: 'from-amber-600 to-amber-700',
};

const MEDAL_ICONS = {
  1: '🥇',
  2: '🥈',
  3: '🥉',
};

export default function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchLeaderboard = async () => {
    try {
      const data = await getLeaderboard();
      setLeaderboard(data.leaderboard || []);
      setLastUpdated(new Date(data.calculated_at));
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
    // Refresh every 30 seconds
    const interval = setInterval(fetchLeaderboard, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 rounded-2xl p-6 shadow-xl">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-white/10 rounded w-3/4"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-white/10 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 rounded-2xl p-6 shadow-xl border border-white/10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-2xl">🏆</span>
          Top 5 Today
        </h2>
        <span className="text-xs text-purple-300">24h rolling</span>
      </div>

      {leaderboard.length === 0 ? (
        <p className="text-purple-200 text-center py-8">
          No karma earned in the last 24 hours yet!
          <br />
          <span className="text-sm opacity-75">Be the first to get likes!</span>
        </p>
      ) : (
        <div className="space-y-3">
          {leaderboard.map((user, index) => (
            <div
              key={user.id}
              className={`relative flex items-center gap-4 p-3 rounded-xl transition-all duration-300 hover:scale-[1.02] ${
                index < 3
                  ? `bg-gradient-to-r ${MEDAL_COLORS[index + 1]} bg-opacity-20`
                  : 'bg-white/5 hover:bg-white/10'
              }`}
            >
              {/* Rank */}
              <div className="w-10 h-10 flex items-center justify-center text-2xl">
                {index < 3 ? (
                  MEDAL_ICONS[index + 1]
                ) : (
                  <span className="text-purple-300 font-bold">{index + 1}</span>
                )}
              </div>

              {/* Avatar */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${
                index === 0 ? 'bg-yellow-500' :
                index === 1 ? 'bg-slate-400' :
                index === 2 ? 'bg-amber-600' :
                'bg-purple-600'
              }`}>
                {user.username[0].toUpperCase()}
              </div>

              {/* Name */}
              <div className="flex-1">
                <p className="text-white font-medium">{user.username}</p>
              </div>

              {/* Karma */}
              <div className="text-right">
                <p className="text-white font-bold text-lg">{user.karma}</p>
                <p className="text-purple-300 text-xs">karma</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {lastUpdated && (
        <p className="text-purple-300/60 text-xs mt-4 text-center">
          Updated {lastUpdated.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
