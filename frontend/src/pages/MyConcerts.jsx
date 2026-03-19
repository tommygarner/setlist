import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import ConcertCard from '../components/ConcertCard'

const STATUS_LABEL = { going: '✅ Going', interested: '⭐ Interested' }

export default function MyConcerts() {
  const { user } = useAuth()
  const [concerts, setConcerts] = useState([])
  const [attendance, setAttendance] = useState({})
  const [tab, setTab] = useState('All')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    Promise.all([
      supabase.from('concerts_discovered').select('*').eq('user_id', user.id).order('date'),
      supabase.from('concert_attendance').select('event_id, status').eq('user_id', user.id),
    ]).then(([c, a]) => {
      setConcerts(c.data ?? [])
      const map = {}
      a.data?.forEach((r) => { map[r.event_id] = r.status })
      setAttendance(map)
      setLoading(false)
    })
  }, [user])

  const setStatus = async (eventId, status) => {
    const current = attendance[eventId]
    if (current === status) {
      await supabase.from('concert_attendance').delete().eq('user_id', user.id).eq('event_id', eventId)
      setAttendance((a) => { const n = { ...a }; delete n[eventId]; return n })
    } else {
      await supabase.from('concert_attendance').upsert({ user_id: user.id, event_id: eventId, status }, { onConflict: 'user_id,event_id' })
      setAttendance((a) => ({ ...a, [eventId]: status }))
    }
  }

  const filtered = tab === 'All'
    ? concerts
    : concerts.filter((c) => attendance[c.event_id] === tab.toLowerCase())

  if (loading) return <div className="flex justify-center pt-20"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" /></div>

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-white">My Concerts</h1>
      <p className="mt-1 text-sm text-gray-400">Your saved shows and attendance</p>

      <div className="mt-6 flex gap-2">
        {['All', 'Going', 'Interested'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t ? 'bg-brand text-black' : 'bg-surface text-gray-400 hover:text-white'
            }`}
          >
            {t} {t === 'All' ? `(${concerts.length})` : `(${concerts.filter(c => attendance[c.event_id] === t.toLowerCase()).length})`}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-3">
        {filtered.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500">
            {tab === 'All' ? 'No concerts saved yet.' : `No concerts marked as ${tab}.`}
          </p>
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
