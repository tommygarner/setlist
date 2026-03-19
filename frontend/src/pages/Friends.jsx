import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const TABS = ['My Friends', 'Find Friends', 'Requests']

export default function Friends() {
  const [tab, setTab] = useState('My Friends')
  const [friends, setFriends] = useState([])
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getFriends()
      .then(setFriends)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const search = async () => {
    if (!query.trim()) return
    try {
      const data = await api.searchUsers(query)
      setResults(data ?? [])
    } catch {
      setResults([])
    }
  }

  const addFriend = async (friendId) => {
    try {
      await api.sendFriendRequest(friendId)
      alert('Friend request sent!')
      setResults([])
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-white">Friends</h1>
      <p className="mt-1 text-sm text-gray-400">Connect with people who share your music taste</p>

      <div className="mt-6 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t ? 'bg-brand text-black' : 'bg-surface text-gray-400 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'My Friends' && (
          loading ? (
            <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" /></div>
          ) : friends.length === 0 ? (
            <p className="py-12 text-center text-sm text-gray-500">No friends yet. Search for users to add them.</p>
          ) : (
            <div className="space-y-3">
              {friends.map((f) => (
                <div key={f.id} className="flex items-center justify-between rounded-xl bg-surface p-4">
                  <div>
                    <p className="font-medium text-white">{f.username}</p>
                    <p className="text-xs text-gray-400">{f.email}</p>
                  </div>
                  <a href="/messages" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-400 transition-colors hover:text-white">Message</a>
                </div>
              ))}
            </div>
          )
        )}

        {tab === 'Find Friends' && (
          <div>
            <div className="flex gap-2">
              <input
                placeholder="Search by username or email"
                value={query} onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && search()}
                className="flex-1 rounded-lg bg-surface px-4 py-2.5 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-brand"
              />
              <button onClick={search} className="rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-black">Search</button>
            </div>
            <div className="mt-4 space-y-3">
              {results.map((u) => (
                <div key={u.id} className="flex items-center justify-between rounded-xl bg-surface p-4">
                  <div>
                    <p className="font-medium text-white">{u.username}</p>
                    <p className="text-xs text-gray-400">{u.email}</p>
                  </div>
                  <button onClick={() => addFriend(u.id)} className="rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-black">Add</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'Requests' && (
          <p className="py-12 text-center text-sm text-gray-500">Friend requests — coming soon</p>
        )}
      </div>
    </div>
  )
}
