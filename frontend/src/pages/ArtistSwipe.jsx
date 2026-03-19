import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { supabase } from '../lib/supabase'
import { useAuth } from '../contexts/AuthContext'

const SESSION_KEY = 'swipe_idx'

function openLink(url) {
  // Force new tab — avoids navigating away from the swipe screen
  window.open(url, '_blank', 'noopener,noreferrer')
}

export default function ArtistSwipe() {
  const { user } = useAuth()
  const [artists, setArtists] = useState([])
  const [idx, setIdx] = useState(() => {
    const saved = sessionStorage.getItem(SESSION_KEY)
    return saved ? parseInt(saved, 10) : 0
  })
  const [artistInfo, setArtistInfo] = useState(null)
  const [tracks, setTracks] = useState([])
  const [albums, setAlbums] = useState([])
  const [loading, setLoading] = useState(true)
  const [infoLoading, setInfoLoading] = useState(false)
  const [liked, setLiked] = useState([])
  const [passed, setPassed] = useState([])
  const [error, setError] = useState('')

  // Persist idx across navigation
  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, String(idx))
  }, [idx])

  // Load artist queue from Supabase (fast — no Spotify calls)
  useEffect(() => {
    if (!user) return
    setError('')
    Promise.all([
      supabase.from('concerts_discovered').select('artist_name').eq('user_id', user.id),
      supabase.from('preferences').select('artist_name, preference').eq('user_id', user.id),
    ])
      .then(([concerts, prefs]) => {
        if (concerts.error) throw concerts.error
        if (prefs.error) throw prefs.error

        const rated = new Set(prefs.data?.map((p) => p.artist_name) ?? [])
        const likedList = prefs.data?.filter((p) => p.preference === 'liked').map((p) => p.artist_name) ?? []
        const passedList = prefs.data?.filter((p) => p.preference === 'disliked').map((p) => p.artist_name) ?? []
        const unrated = [...new Set(concerts.data?.map((c) => c.artist_name) ?? [])].filter(
          (a) => a && !rated.has(a)
        )
        setArtists(unrated)
        setLiked(likedList)
        setPassed(passedList)

        // Clamp saved idx in case queue shrank since last visit
        setIdx((i) => Math.min(i, Math.max(0, unrated.length - 1)))
      })
      .catch((err) => setError(err.message || 'Failed to load swipe queue'))
      .finally(() => setLoading(false))
  }, [user])

  // Fetch current artist info (served from cache if available)
  useEffect(() => {
    const artist = artists[idx]
    if (!artist) return
    setInfoLoading(true)
    setArtistInfo(null)
    setTracks([])
    setAlbums([])
    Promise.all([
      api.getArtistInfo(artist).catch(() => null),
      api.getArtistTracks(artist).catch(() => []),
      api.getArtistAlbums(artist).catch(() => []),
    ]).then(([info, t, a]) => {
      setArtistInfo(info)
      setTracks(t ?? [])
      setAlbums(a ?? [])
      setInfoLoading(false)
    })

    // Prefetch the next artist while user reads the current one
    api.prefetchArtist(artists[idx + 1])
  }, [idx, artists])

  const swipe = async (preference) => {
    const artist = artists[idx]
    await api.savePreference(artist, preference)
    if (preference === 'liked') setLiked((l) => [...l, artist])
    else setPassed((p) => [...p, artist])
    setIdx((i) => i + 1)
  }

  if (loading) return (
    <div className="flex justify-center pt-20">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
    </div>
  )

  if (error) return (
    <div className="mx-auto max-w-lg pt-12 text-center">
      <p className="text-lg font-semibold text-white">Could not load artists</p>
      <p className="mt-2 text-sm text-red-400">{error}</p>
    </div>
  )

  if (artists.length === 0) return (
    <div className="mx-auto max-w-lg pt-12 text-center">
      <p className="text-lg font-semibold text-white">No artists to swipe on</p>
      <p className="mt-2 text-sm text-gray-400">Discover concerts first to populate your swipe queue.</p>
      <a href="/discover" className="mt-6 inline-block rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-black">
        Discover Concerts
      </a>
    </div>
  )

  if (idx >= artists.length) return (
    <div className="mx-auto max-w-lg pt-12 text-center">
      <p className="text-3xl mb-3">🎉</p>
      <p className="text-lg font-semibold text-white">All caught up!</p>
      <p className="mt-1 text-sm text-gray-400">Liked {liked.length} · Passed {passed.length}</p>
      <a href="/discovery" className="mt-6 inline-block rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-black">
        See Recommendations
      </a>
    </div>
  )

  const artist = artists[idx]
  const progress = (idx / artists.length) * 100

  return (
    <div className="mx-auto max-w-2xl">
      {/* Progress */}
      <div className="mb-4 flex items-center justify-between text-xs text-gray-500">
        <span>{idx} / {artists.length} artists</span>
        <span>✅ {liked.length} · ❌ {passed.length}</span>
      </div>
      <div className="mb-6 h-1 rounded-full bg-white/10">
        <div className="h-1 rounded-full bg-brand transition-all" style={{ width: `${progress}%` }} />
      </div>

      {/* Artist card */}
      <div className="rounded-xl border border-white/10 bg-surface overflow-hidden">
        {infoLoading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex gap-6 p-6">
              {artistInfo?.image ? (
                <img src={artistInfo.image} alt={artist} className="h-32 w-32 flex-shrink-0 rounded-lg object-cover" />
              ) : (
                <div className="flex h-32 w-32 flex-shrink-0 items-center justify-center rounded-lg bg-white/5 text-4xl">🎤</div>
              )}
              <div>
                <h2 className="text-2xl font-bold text-white">{artist}</h2>
                {artistInfo?.followers && (
                  <p className="mt-1 text-sm text-gray-400">{artistInfo.followers.toLocaleString()} followers</p>
                )}
                {artistInfo?.genres?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {artistInfo.genres.slice(0, 3).map((g) => (
                      <span key={g} className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs text-gray-300">{g}</span>
                    ))}
                  </div>
                )}
                {artistInfo?.spotify_url && (
                  <button
                    onClick={() => openLink(artistInfo.spotify_url)}
                    className="mt-3 rounded px-2.5 py-1 text-xs text-[#1DB954] ring-1 ring-[#1DB954]/30 hover:bg-[#1DB954]/10"
                  >
                    Open in Spotify
                  </button>
                )}
              </div>
            </div>

            {/* Top Tracks */}
            {tracks.length > 0 && (
              <div className="border-t border-white/10 px-6 pb-2 pt-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Top Tracks</p>
                <div className="space-y-2">
                  {tracks.slice(0, 5).map((t, i) => (
                    <div key={i} className="flex items-center gap-3">
                      {t.album_image && (
                        <img src={t.album_image} alt="" className="h-9 w-9 rounded object-cover flex-shrink-0" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-white">{t.name}</p>
                        <p className="truncate text-xs text-gray-500">{t.album_name}</p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        {t.spotify_url && (
                          <button
                            onClick={() => openLink(t.spotify_url)}
                            className="rounded px-2 py-1 text-xs text-[#1DB954] ring-1 ring-[#1DB954]/30 hover:bg-[#1DB954]/10"
                          >
                            Spotify
                          </button>
                        )}
                        <button
                          onClick={() => openLink(`https://www.youtube.com/results?search_query=${encodeURIComponent(`${t.artist} ${t.name} official audio`)}`)}
                          className="rounded px-2 py-1 text-xs text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/10"
                        >
                          YT
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Albums */}
            {albums.length > 0 && (
              <div className="border-t border-white/10 px-6 py-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Albums</p>
                <div className="flex gap-3">
                  {albums.slice(0, 3).map((a, i) => (
                    <button
                      key={i}
                      onClick={() => openLink(a.spotify_url)}
                      className="group w-20 flex-shrink-0 text-left"
                    >
                      {a.image && (
                        <img src={a.image} alt={a.name} className="w-20 h-20 rounded-lg object-cover transition-opacity group-hover:opacity-80" />
                      )}
                      <p className="mt-1.5 truncate text-xs text-gray-400 group-hover:text-white">{a.name}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Swipe buttons */}
      <div className="mt-6 flex gap-4">
        <button
          onClick={() => swipe('disliked')}
          className="flex-1 rounded-xl border border-white/10 py-4 text-lg font-semibold text-gray-400 transition-colors hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400"
        >
          ❌ Pass
        </button>
        <button
          onClick={() => swipe('liked')}
          className="flex-1 rounded-xl bg-brand py-4 text-lg font-semibold text-black transition-opacity hover:opacity-90"
        >
          ✅ Like
        </button>
      </div>
    </div>
  )
}
