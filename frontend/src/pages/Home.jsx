import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'

const STEPS = [
  { to: '/connect-spotify', icon: '🎵', label: 'Connect Spotify',    desc: 'Link your music library' },
  { to: '/discover',        icon: '🎤', label: 'Discover Concerts',  desc: 'Find shows near you' },
  { to: '/swipe',           icon: '🎸', label: 'Swipe on Artists',   desc: 'Like or pass' },
  { to: '/discovery',       icon: '✨', label: 'Get Recommendations', desc: 'Personalized picks' },
]

export default function Home() {
  const { user } = useAuth()
  const [stats, setStats] = useState({ liked: 0, disliked: 0, concerts: 0 })

  useEffect(() => {
    if (!user) return
    Promise.all([
      supabase.from('preferences').select('preference').eq('user_id', user.id),
      supabase.from('concerts_discovered').select('event_id').eq('user_id', user.id),
    ]).then(([prefs, concerts]) => {
      const liked = prefs.data?.filter((p) => p.preference === 'liked').length ?? 0
      const disliked = prefs.data?.filter((p) => p.preference === 'disliked').length ?? 0
      setStats({ liked, disliked, concerts: concerts.data?.length ?? 0 })
    })
  }, [user])

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-white">Welcome back</h1>
      <p className="mt-1 text-sm text-gray-400">{user?.email}</p>

      <div className="mt-6 grid grid-cols-3 gap-4">
        {[
          { label: 'Artists liked',    value: stats.liked },
          { label: 'Artists passed',   value: stats.disliked },
          { label: 'Concerts saved',   value: stats.concerts },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl bg-surface p-4 text-center">
            <p className="text-2xl font-bold text-brand">{value}</p>
            <p className="mt-1 text-xs text-gray-400">{label}</p>
          </div>
        ))}
      </div>

      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wider text-gray-500">Get started</h2>
      <div className="mt-3 grid grid-cols-2 gap-3">
        {STEPS.map(({ to, icon, label, desc }) => (
          <Link
            key={to} to={to}
            className="flex items-center gap-3 rounded-xl border border-white/10 bg-surface p-4 transition-colors hover:border-brand/50 hover:bg-brand/5"
          >
            <span className="text-2xl">{icon}</span>
            <div>
              <p className="text-sm font-medium text-white">{label}</p>
              <p className="text-xs text-gray-400">{desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
