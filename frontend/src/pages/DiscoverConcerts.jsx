import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'
import ConcertCard from '../components/ConcertCard'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function fetchArtistImages(artistNames) {
  const imageMap = {}
  await Promise.allSettled(
    artistNames.map(async (name) => {
      try {
        const info = await api.getArtistInfo(name)
        if (info.image) imageMap[name] = info.image
      } catch {
        // not on Spotify
      }
    })
  )
  return imageMap
}

function ProgressBar({ step, pct }) {
  return (
    <div className="rounded-xl border border-white/10 bg-surface p-5">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="text-gray-300">{step}</span>
        <span className="tabular-nums text-gray-500">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-brand transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function DiscoverConcerts() {
  const [concerts, setConcerts] = useState([])
  const [imageMap, setImageMap] = useState({})
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)
  const [progress, setProgress] = useState(null) // {step, pct} | null
  const [cacheMsg, setCacheMsg] = useState('')
  const [error, setError] = useState('')
  const [city, setCity] = useState('Austin')
  const [state, setState] = useState('TX')
  const [radius, setRadius] = useState(25)
  const [filter, setFilter] = useState('')
  const imageMapRef = useRef({})

  const enrich = async (list) => {
    const names = [...new Set(list.map((c) => c.artist_name).filter(Boolean))]
    const newNames = names.filter((n) => !(n in imageMapRef.current))
    if (newNames.length === 0) return
    const fetched = await fetchArtistImages(newNames)
    imageMapRef.current = { ...imageMapRef.current, ...fetched }
    setImageMap({ ...imageMapRef.current })
  }

  useEffect(() => {
    api.getConcerts()
      .then((list) => {
        setConcerts(list)
        enrich(list)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleDiscover = async (force = false) => {
    setDiscovering(true)
    setError('')
    setCacheMsg('')
    setProgress({ step: 'Starting…', pct: 0 })

    try {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      if (!token) throw new Error('Not logged in')

      const res = await fetch(
        `${API_URL}/api/concerts/discover?city=${encodeURIComponent(city)}&state=${encodeURIComponent(state)}&radius=${radius}&force=${force}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        }
      )

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            setProgress({ step: evt.step, pct: evt.progress })
            if (evt.error) {
              setError(evt.step)
              setProgress(null)
              setDiscovering(false)
              return
            }
            if (evt.done) {
              if (evt.cached) setCacheMsg(evt.step)
              const list = await api.getConcerts()
              setConcerts(list)
              enrich(list)
            }
          } catch {
            // malformed line — skip
          }
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setDiscovering(false)
      setProgress(null)
    }
  }

  const filtered = filter
    ? concerts.filter(
        (c) =>
          c.artist_name?.toLowerCase().includes(filter.toLowerCase()) ||
          c.venue_name?.toLowerCase().includes(filter.toLowerCase())
      )
    : concerts

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-white">Discover Concerts</h1>
      <p className="mt-1 text-sm text-gray-400">Find shows from your Spotify artists via Ticketmaster and SeatGeek</p>

      {/* Search settings */}
      <div className="mt-6 flex flex-wrap items-end gap-3 rounded-xl border border-white/10 bg-surface p-4">
        <div>
          <label className="mb-1 block text-xs text-gray-400">City</label>
          <input
            value={city} onChange={(e) => setCity(e.target.value)}
            className="rounded-lg bg-base px-3 py-2 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-400">State</label>
          <input
            value={state} onChange={(e) => setState(e.target.value)} maxLength={2}
            className="w-16 rounded-lg bg-base px-3 py-2 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-400">Radius (mi)</label>
          <input
            type="number" value={radius} onChange={(e) => setRadius(Number(e.target.value))} min={10} max={500}
            className="w-24 rounded-lg bg-base px-3 py-2 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-brand"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleDiscover(false)} disabled={discovering}
            className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {discovering ? 'Searching…' : 'Discover'}
          </button>
          <button
            onClick={() => handleDiscover(true)} disabled={discovering}
            title="Ignore cache and re-fetch from APIs"
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-gray-400 transition-colors hover:text-white disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {progress && (
        <div className="mt-4">
          <ProgressBar step={progress.step} pct={progress.pct} />
        </div>
      )}

      {/* Cache notice */}
      {cacheMsg && !discovering && (
        <p className="mt-3 text-xs text-gray-500">{cacheMsg}</p>
      )}

      {/* Error */}
      {error && (
        <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {/* Filter */}
      {!discovering && concerts.length > 0 && (
        <div className="mt-4">
          <input
            placeholder="Filter by artist or venue…"
            value={filter} onChange={(e) => setFilter(e.target.value)}
            className="w-full rounded-lg bg-surface px-4 py-2.5 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-brand"
          />
          <p className="mt-2 text-xs text-gray-500">Showing {filtered.length} of {concerts.length} concerts</p>
        </div>
      )}

      {/* Concert list */}
      <div className="mt-4 space-y-3">
        {loading ? (
          <p className="py-12 text-center text-sm text-gray-500">Loading saved concerts…</p>
        ) : !discovering && filtered.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500">
            {concerts.length === 0
              ? 'No concerts yet. Connect Spotify then click Discover.'
              : 'No concerts match your filter.'}
          </p>
        ) : (
          filtered.map((c) => (
            <ConcertCard
              key={c.event_id}
              concert={{ ...c, artist_image: imageMap[c.artist_name] ?? null }}
            />
          ))
        )}
      </div>
    </div>
  )
}
