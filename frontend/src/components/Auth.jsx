import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export function LoginForm({ onSwitch }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full bg-slate-800 text-slate-200 rounded-lg px-4 py-2 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
          placeholder="Enter username"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full bg-slate-800 text-slate-200 rounded-lg px-4 py-2 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
          placeholder="Enter password"
          required
        />
      </div>
      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-medium rounded-lg transition-all disabled:opacity-50"
      >
        {isLoading ? 'Signing in...' : 'Sign In'}
      </button>
      <p className="text-center text-slate-400 text-sm">
        Don't have an account?{' '}
        <button
          type="button"
          onClick={onSwitch}
          className="text-purple-400 hover:text-purple-300"
        >
          Register
        </button>
      </p>
      <p className="text-center text-slate-500 text-xs mt-4">
        Demo accounts: alice, bob, charlie, diana<br />
        Password: password123
      </p>
    </form>
  );
}

export function RegisterForm({ onSwitch }) {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await register(username, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full bg-slate-800 text-slate-200 rounded-lg px-4 py-2 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
          placeholder="Choose a username"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full bg-slate-800 text-slate-200 rounded-lg px-4 py-2 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
          placeholder="Create a password"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Confirm Password
        </label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full bg-slate-800 text-slate-200 rounded-lg px-4 py-2 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
          placeholder="Confirm your password"
          required
        />
      </div>
      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-medium rounded-lg transition-all disabled:opacity-50"
      >
        {isLoading ? 'Creating account...' : 'Create Account'}
      </button>
      <p className="text-center text-slate-400 text-sm">
        Already have an account?{' '}
        <button
          type="button"
          onClick={onSwitch}
          className="text-purple-400 hover:text-purple-300"
        >
          Sign In
        </button>
      </p>
    </form>
  );
}

export function AuthModal({ isOpen, onClose }) {
  const [mode, setMode] = useState('login');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-2xl p-6 w-full max-w-md border border-slate-700 shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">
            {mode === 'login' ? 'Welcome Back' : 'Join the Community'}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {mode === 'login' ? (
          <LoginForm onSwitch={() => setMode('register')} />
        ) : (
          <RegisterForm onSwitch={() => setMode('login')} />
        )}
      </div>
    </div>
  );
}
