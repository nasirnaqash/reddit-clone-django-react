import { createContext, useContext, useState, useEffect } from 'react';
import * as api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize CSRF and check if user is logged in
    async function init() {
      try {
        await api.initCSRF();
        const userData = await api.getCurrentUser();
        setUser(userData);
      } catch (error) {
        // Not logged in
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const login = async (username, password) => {
    const userData = await api.login(username, password);
    setUser(userData);
    return userData;
  };

  const register = async (username, password) => {
    const userData = await api.register(username, password);
    setUser(userData);
    return userData;
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
