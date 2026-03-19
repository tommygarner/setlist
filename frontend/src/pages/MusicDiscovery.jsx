import { useState } from 'react'
import { api } from '../lib/api'
import ConcertCard from '../components/ConcertCard'

const TABS = ['For You', 'Similar Artists', 'This Weekend', 'Surprise Me']

function normalize(item) {
  const e = item.event ?? item
  const performer = e.performers?.[0]
  const dt = e.datetime_local ?? ''
  const [date, time] = dt.split('T')
  return {
    event_id: e.id ? `sg_${e.id}` : null,
    event_name: e.title ?? e.name ?? '',
    artist_name: e._matched_artist ?? performer?.name ?? '',
    artist_image: performer?.image ?? null,
    venue_name: e.venue?.name ?? '',
    city: e.venue?.city ?? '',
    state: e.venue?.state ?? '',
    date: date ?? '',
    time: time ?? '',
    ticket_url: e.url ?? '',
    min_price: e.stats?.lowest_price ?? null,
    max_price: e.stats?.highest_price ?? null,
    score: item.score ?? e.score ?? null,
    because_of: e._because_of ?? null,
    source: 'seatgeek',
  }
}

export default function MusicDiscovery() {
  const [tab, setTab] = useState('For You')
  const [events, setEvents] = useState([])
  const [hint, setHint] = useState('')
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setSearched(true)
    setError('')
    setHint('')
    try {
      const loaders = {
        'For You': api.getForYouDiscovery,
        'Similar Artists': api.getSimilarDiscovery,
        'This Weekend': api.getWeekendDiscovery,
        'Surprise Me': api.getSurpriseDiscovery,
      }
      const data = await loaders[tab]()
      if (data.hint) setHint(data.hint)
      setEvents((data.events ?? []).map(normalize))
    } catch (err) {
      setEvents([])
      setError(err.message || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-white">Music Discovery</h1>
      <p className="mt-1 text-sm text-gray-400">Personalized concert recommendations for Austin</p>

      <div className="mt-6 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setSearched(false); setEvents([]); setHint('') }}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t ? 'bg-brand text-black' : 'bg-surface text-gray-400 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab descriptions */}
      <p className="mt-2 text-xs text-gray-500">
        {tab === 'For You' && 'Shows featuring artists you\'ve liked via Artist Swipe.'}
        {tab === 'Similar Artists' && 'Artists similar to ones you love — discovered via Spotify.'}
        {tab === 'This Weekend' && 'Upcoming shows this Friday through Sunday, your liked artists first.'}
        {tab === 'Surprise Me' && 'One random highly-rated show you might not have heard of.'}
      </p>

      <div className="mt-4">
        <button
          onClick={load} disabled={loading}
          className="rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Loading…' : `Load ${tab}`}
        </button>
      </div>

      <div className="mt-6 space-y-3">
        {error && (
          <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>
        )}
        {hint && !loading && (
          <p className="rounded-lg border border-white/10 bg-surface px-4 py-3 text-sm text-gray-400">{hint}</p>
        )}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : events.length > 0 ? (
          events.map((e) => (
            <div key={e.event_id ?? e.event_name}>
              {e.because_of && (
                <p className="mb-1 px-1 text-xs text-gray-500">
                  Because you like <span className="text-brand">{e.because_of}</span>
                </p>
              )}
              <ConcertCard concert={e} />
            </div>
          ))
        ) : searched && !hint ? (
          <p className="py-12 text-center text-sm text-gray-500">No concerts found. Try another tab.</p>
        ) : null}
      </div>
    </div>
  )
}
