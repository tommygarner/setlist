import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import ConcertCard from '../components/ConcertCard'

export default function DiscoverConcerts() {
  const [concerts, setConcerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)
  const [city, setCity] = useState('Austin')
  const [state, setState] = useState('TX')
  const [radius, setRadius] = useState(100)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    api.getConcerts()
      .then(setConcerts)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleDiscover = async () => {
    setDiscovering(true)
    try {
      const result = await api.discoverConcerts(city, state, radius)
      setConcerts(result.concerts ?? [])
    } catch (err) {
      alert(err.message)
    } finally {
      setDiscovering(false)
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
        <button
          onClick={handleDiscover} disabled={discovering}
          className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {discovering ? 'Searching…' : 'Discover'}
        </button>
      </div>

      {/* Filter */}
      {concerts.length > 0 && (
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
        ) : filtered.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500">
            {concerts.length === 0
              ? 'No concerts yet. Connect Spotify then click Discover.'
              : 'No concerts match your filter.'}
          </p>
        ) : (
          filtered.map((c) => <ConcertCard key={c.event_id} concert={c} />)
        )}
      </div>
    </div>
  )
}
