const API_BASE = '/api';

// Get CSRF token from cookies
function getCSRFToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith(name + '=')) {
      return cookie.substring(name.length + 1);
    }
  }
  return null;
}

// Fetch wrapper with error handling
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  // Add CSRF token for non-GET requests
  if (options.method && options.method !== 'GET') {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || error.detail || 'Request failed');
  }
  
  return response.json();
}

// Initialize CSRF token
export async function initCSRF() {
  return fetchAPI('/csrf/');
}

// Auth endpoints
export async function login(username, password) {
  return fetchAPI('/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function register(username, password) {
  return fetchAPI('/register/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function logout() {
  return fetchAPI('/logout/', { method: 'POST' });
}

export async function getCurrentUser() {
  return fetchAPI('/me/');
}

// Posts endpoints
export async function getPosts(page = 1) {
  return fetchAPI(`/posts/?page=${page}`);
}

export async function getPost(id) {
  return fetchAPI(`/posts/${id}/`);
}

export async function createPost(content) {
  return fetchAPI('/posts/', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function likePost(postId) {
  return fetchAPI(`/posts/${postId}/like/`, { method: 'POST' });
}

export async function unlikePost(postId) {
  return fetchAPI(`/posts/${postId}/unlike/`, { method: 'POST' });
}

// Comments endpoints
export async function createComment(postId, content, parentId = null) {
  return fetchAPI('/comments/', {
    method: 'POST',
    body: JSON.stringify({ post: postId, content, parent: parentId }),
  });
}

export async function likeComment(commentId) {
  return fetchAPI(`/comments/${commentId}/like/`, { method: 'POST' });
}

export async function unlikeComment(commentId) {
  return fetchAPI(`/comments/${commentId}/unlike/`, { method: 'POST' });
}

// Leaderboard
export async function getLeaderboard() {
  return fetchAPI('/leaderboard/');
}
