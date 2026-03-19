import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'

export default function ConnectSpotify() {
  const { user } = useAuth()
  const [connected, setConnected] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    if (!user) return
    supabase
      .from('profiles')
      .select('spotify_connected, spotify_token_expires_at')
      .eq('id', user.id)
      .single()
      .then(({ data }) => {
        if (data?.spotify_connected && data?.spotify_token_expires_at) {
          const expires = new Date(data.spotify_token_expires_at)
          setConnected(expires > new Date())
        }
        setChecking(false)
      })
  }, [user])

  // Spotify PKCE or redirect is handled by the backend /api/spotify/auth endpoint
  const handleConnect = () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/spotify/auth?user_id=${user.id}`
  }

  const handleDisconnect = async () => {
    await supabase.from('profiles').update({
      spotify_connected: false,
      spotify_access_token: null,
      spotify_refresh_token: null,
      spotify_token_expires_at: null,
    }).eq('id', user.id)
    setConnected(false)
  }

  if (checking) {
    return <div className="flex justify-center pt-20"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" /></div>
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="text-2xl font-bold text-white">Connect Spotify</h1>
      <p className="mt-1 text-sm text-gray-400">Link your library to discover concerts from artists you love</p>

      <div className="mt-8 rounded-xl border border-white/10 bg-surface p-6">
        {connected ? (
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand/20 text-3xl">✅</div>
            <p className="font-semibold text-white">Spotify is connected</p>
            <p className="mt-1 text-sm text-gray-400">Your liked songs and top artists are available</p>
            <div className="mt-6 flex gap-3">
              <a href="/discover" className="flex-1 rounded-lg bg-brand py-2.5 text-center text-sm font-semibold text-black transition-opacity hover:opacity-90">
                Discover Concerts
              </a>
              <button onClick={handleDisconnect} className="flex-1 rounded-lg border border-white/10 py-2.5 text-sm text-gray-400 transition-colors hover:text-white">
                Disconnect
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#1DB954]/20 text-3xl">🎵</div>
            <p className="font-semibold text-white">Connect your Spotify</p>
            <p className="mt-2 text-sm text-gray-400">We'll read your liked songs and top artists to find concerts near you</p>
            <ul className="mt-4 space-y-1 text-left text-xs text-gray-500">
              <li>• Your liked songs</li>
              <li>• Your top artists</li>
              <li>• Read-only access</li>
            </ul>
            <button
              onClick={handleConnect}
              className="mt-6 w-full rounded-lg bg-brand py-3 text-sm font-semibold text-black transition-opacity hover:opacity-90"
            >
              Connect Spotify
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
