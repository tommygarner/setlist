import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function authHeaders() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function request(path, options = {}) {
  const headers = await authHeaders()
  const res = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

export const api = {
  // Concert discovery
  discoverConcerts: (city, state, radius) =>
    request(`/api/concerts/discover?city=${city}&state=${state}&radius=${radius}`, { method: 'POST' }),

  getConcerts: () => request('/api/concerts'),

  // Artist info
  getArtistInfo: (name) => request(`/api/artists/${encodeURIComponent(name)}/info`),
  getArtistTracks: (name) => request(`/api/artists/${encodeURIComponent(name)}/tracks`),
  getArtistAlbums: (name) => request(`/api/artists/${encodeURIComponent(name)}/albums`),

  // Preferences
  savePreference: (artistName, preference) =>
    request('/api/preferences', {
      method: 'POST',
      body: JSON.stringify({ artist_name: artistName, preference }),
    }),
  getPreferences: () => request('/api/preferences'),

  // Friends
  getFriends: () => request('/api/friends'),
  searchUsers: (query) => request(`/api/friends/search?q=${encodeURIComponent(query)}`),
  sendFriendRequest: (friendId) =>
    request('/api/friends/request', { method: 'POST', body: JSON.stringify({ friend_id: friendId }) }),

  // Messages
  getMessages: (friendId) => request(`/api/messages/${friendId}`),
  sendMessage: (friendId, message, concertData = null) =>
    request('/api/messages', {
      method: 'POST',
      body: JSON.stringify({ receiver_id: friendId, message, concert_data: concertData }),
    }),
}
