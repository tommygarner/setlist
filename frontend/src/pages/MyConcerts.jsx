import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import ConcertCard from '../components/ConcertCard'

const STATUS_LABEL = { going: '✅ Going', interested: '⭐ Interested' }

export default function MyConcerts() {
  const { user } = useAuth()
  // savedConcerts: concerts that have a Going or Interested status
  const [savedConcerts, setSavedConcerts] = useState([])
  const [attendance, setAttendance] = useState({}) // event_id → status
  const [tab, setTab] = useState('All')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    Promise.all([
      supabase.from('concert_attendance').select('event_id, status').eq('user_id', user.id),
      supabase.from('concerts_discovered').select('*').eq('user_id', user.id).order('date'),
    ]).then(([att, conc]) => {
      const map = {}
      att.data?.forEach((r) => { map[r.event_id] = r.status })
      setAttendance(map)

      // Only keep concerts that have been explicitly saved (Going or Interested)
      const savedIds = new Set(Object.keys(map))
      setSavedConcerts((conc.data ?? []).filter((c) => savedIds.has(c.event_id)))
      setLoading(false)
    })
  }, [user])

  const setStatus = async (eventId, status) => {
    const current = attendance[eventId]
    if (current === status) {
      // Toggle off — remove from saved list
      await supabase.from('concert_attendance').delete().eq('user_id', user.id).eq('event_id', eventId)
      setAttendance((a) => { const n = { ...a }; delete n[eventId]; return n })
      setSavedConcerts((cs) => cs.filter((c) => c.event_id !== eventId))
    } else {
      await supabase.from('concert_attendance').upsert(
        { user_id: user.id, event_id: eventId, status },
        { onConflict: 'user_id,event_id' }
      )
      setAttendance((a) => ({ ...a, [eventId]: status }))
    }
  }

  const filtered = tab === 'All'
    ? savedConcerts
    : savedConcerts.filter((c) => attendance[c.event_id] === tab.toLowerCase())

  const countFor = (t) => savedConcerts.filter((c) => attendance[c.event_id] === t.toLowerCase()).length

  if (loading) return (
    <div className="flex justify-center pt-20">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
    </div>
  )

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-white">My Concerts</h1>
      <p className="mt-1 text-sm text-gray-400">Shows you've saved as Going or Interested</p>

      <div className="mt-6 flex gap-2">
        {['All', 'Going', 'Interested'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t ? 'bg-brand text-black' : 'bg-surface text-gray-400 hover:text-white'
            }`}
          >
            {t} ({t === 'All' ? savedConcerts.length : countFor(t)})
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-3">
        {filtered.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-gray-500">
              {tab === 'All'
                ? 'No saved concerts yet. Go to Discover Concerts and mark shows as Going or Interested.'
                : `No concerts marked as ${tab}.`}
            </p>
            {tab === 'All' && (
              <a href="/discover" className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-black">
                Discover Concerts
              </a>
            )}
          </div>
        ) : (
          filtered.map((c) => (
            <ConcertCard
              key={c.event_id}
              concert={c}
              actions={
                <div className="flex flex-col gap-1.5">
                  {['going', 'interested'].map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatus(c.event_id, s)}
                      className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${
                        attendance[c.event_id] === s
                          ? 'bg-brand text-black'
                          : 'border border-white/10 text-gray-400 hover:text-white'
                      }`}
                    >
                      {STATUS_LABEL[s]}
                    </button>
                  ))}
                </div>
              }
            />
          ))
        )}
      </div>
    </div>
  )
}
