import { AuthProvider } from './context/AuthContext';
import Header from './components/Header';
import Feed from './components/Feed';
import Leaderboard from './components/Leaderboard';

function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <Header />
        
        <main className="max-w-6xl mx-auto px-4 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Feed */}
            <div className="lg:col-span-2">
              <Feed />
            </div>

            {/* Sidebar with Leaderboard */}
            <div className="lg:col-span-1">
              <div className="sticky top-24">
                <Leaderboard />
                
                {/* Karma Info */}
                <div className="mt-6 bg-slate-900/50 backdrop-blur-sm rounded-2xl p-5 border border-slate-800">
                  <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                    <span>✨</span> Karma System
                  </h3>
                  <ul className="space-y-2 text-sm text-slate-400">
                    <li className="flex items-center gap-2">
                      <span className="text-pink-400">❤️</span>
                      <span>Post like = <strong className="text-white">+5 karma</strong></span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-pink-400">💬</span>
                      <span>Comment like = <strong className="text-white">+1 karma</strong></span>
                    </li>
                  </ul>
                  <p className="text-xs text-slate-500 mt-3">
                    Leaderboard shows karma earned in the last 24 hours only.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </AuthProvider>
  );
}

export default App;
