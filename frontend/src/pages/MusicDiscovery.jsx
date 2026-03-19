import { useState } from 'react'
import { api } from '../lib/api'
import ConcertCard from '../components/ConcertCard'

const TABS = ['For You', 'This Weekend', 'Surprise Me']

export default function MusicDiscovery() {
  const [tab, setTab] = useState('For You')
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const load = async () => {
    setLoading(true)
    setSearched(true)
    try {
      const endpoint = {
        'For You': '/api/discovery/for-you',
        'This Weekend': '/api/discovery/this-weekend',
        'Surprise Me': '/api/discovery/surprise',
      }[tab]
      const data = await fetch(endpoint).then((r) => r.json())
      setEvents(data.events ?? [])
    } catch {
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-white">Music Discovery</h1>
      <p className="mt-1 text-sm text-gray-400">Personalized concert recommendations</p>

      <div className="mt-6 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setSearched(false); setEvents([]) }}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t ? 'bg-brand text-black' : 'bg-surface text-gray-400 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-4">
        <button
          onClick={load} disabled={loading}
          className="rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Loading…' : `Load ${tab}`}
        </button>
      </div>

      <div className="mt-6 space-y-3">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : events.length > 0 ? (
          events.map((e) => <ConcertCard key={e.event_id ?? e.id} concert={e} />)
        ) : searched ? (
          <p className="py-12 text-center text-sm text-gray-500">No concerts found. Try another tab.</p>
        ) : null}
      </div>
    </div>
  )
}
