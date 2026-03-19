import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── Session-level artist cache ───────────────────────────────────────────────
// Persists across page navigation, cleared on hard refresh. TTL: 1 hour.
const ARTIST_TTL_MS = 60 * 60 * 1000
const _cache = new Map()

function _get(key) {
  const e = _cache.get(key)
  if (!e) return null
  if (Date.now() - e.ts > ARTIST_TTL_MS) { _cache.delete(key); return null }
  return e.data
}

function _set(key, data) { _cache.set(key, { data, ts: Date.now() }); return data }

// ── In-flight deduplication ──────────────────────────────────────────────────
// If the same artist is requested twice simultaneously, reuse the same promise.
const _inflight = new Map()

function _deduped(key, fetchFn) {
  const cached = _get(key)
  if (cached) return Promise.resolve(cached)
  if (_inflight.has(key)) return _inflight.get(key)
  const p = fetchFn().then((data) => { _set(key, data); _inflight.delete(key); return data })
  _inflight.set(key, p)
  return p
}

// ── Core request ─────────────────────────────────────────────────────────────
async function authHeaders() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request(path, options = {}) {
  const tokenHeaders = await authHeaders()
  const headers = { ...tokenHeaders, ...(options.headers ?? {}) }
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

// ── Public API ────────────────────────────────────────────────────────────────
export const api = {
  // Concert discovery
  discoverConcerts: (city, state, radius) =>
    request(`/api/concerts/discover?city=${city}&state=${state}&radius=${radius}`, { method: 'POST' }),
  getConcerts: () => request('/api/concerts'),

  // Artist info — all three calls are cached + deduplicated
  getArtistInfo: (name) =>
    _deduped(`info:${name}`, () => request(`/api/artists/${encodeURIComponent(name)}/info`)),
  getArtistTracks: (name) =>
    _deduped(`tracks:${name}`, () => request(`/api/artists/${encodeURIComponent(name)}/tracks`)),
  getArtistAlbums: (name) =>
    _deduped(`albums:${name}`, () => request(`/api/artists/${encodeURIComponent(name)}/albums`)),

  // Prefetch all three for an artist — fire and forget, warms the cache
  prefetchArtist: (name) => {
    if (!name) return
    api.getArtistInfo(name).catch(() => {})
    api.getArtistTracks(name).catch(() => {})
    api.getArtistAlbums(name).catch(() => {})
  },

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

  // Discovery
  getForYouDiscovery: () => request('/api/discovery/for-you'),
  getWeekendDiscovery: () => request('/api/discovery/this-weekend'),
  getSurpriseDiscovery: () => request('/api/discovery/surprise'),
  getSimilarDiscovery: () => request('/api/discovery/similar'),
}
