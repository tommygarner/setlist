import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

export default function Messages() {
  const { user } = useAuth()
  const [friends, setFriends] = useState([])
  const [selected, setSelected] = useState(null)
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    api.getFriends().then(setFriends).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selected) return
    api.getMessages(selected.id)
      .then(setMessages)
      .catch(() => {})
  }, [selected])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (e) => {
    e.preventDefault()
    if (!text.trim() || !selected) return
    setSending(true)
    try {
      await api.sendMessage(selected.id, text.trim())
      setText('')
      const updated = await api.getMessages(selected.id)
      setMessages(updated)
    } catch {
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] gap-0 overflow-hidden rounded-xl border border-white/10">
      {/* Friend list */}
      <aside className="w-56 flex-shrink-0 overflow-y-auto border-r border-white/10 bg-surface">
        <div className="px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Chats</p>
        </div>
        {friends.map((f) => (
          <button
            key={f.id}
            onClick={() => setSelected(f)}
            className={`w-full px-4 py-3 text-left transition-colors hover:bg-white/5 ${selected?.id === f.id ? 'border-l-2 border-brand bg-brand/10' : ''}`}
          >
            <p className="text-sm font-medium text-white">{f.username}</p>
          </button>
        ))}
        {friends.length === 0 && (
          <p className="px-4 py-3 text-xs text-gray-500">Add friends to chat</p>
        )}
      </aside>

      {/* Chat area */}
      <div className="flex flex-1 flex-col bg-base">
        {selected ? (
          <>
            <div className="border-b border-white/10 px-5 py-3">
              <p className="font-medium text-white">{selected.username}</p>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 px-5 py-4">
              {messages.map((m) => {
                const mine = m.sender_id === user?.id
                return (
                  <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs rounded-2xl px-4 py-2.5 text-sm ${mine ? 'bg-brand text-black' : 'bg-surface text-white'}`}>
                      {m.message}
                      {m.concert_data && (
                        <div className="mt-2 rounded-lg border border-white/10 bg-black/20 p-2 text-xs">
                          🎤 {m.concert_data.artist_name} · {m.concert_data.venue_name} · {m.concert_data.date}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
              <div ref={bottomRef} />
            </div>

            <form onSubmit={send} className="border-t border-white/10 px-5 py-3 flex gap-2">
              <input
                value={text} onChange={(e) => setText(e.target.value)}
                placeholder={`Message ${selected.username}…`}
                className="flex-1 rounded-lg bg-surface px-4 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-brand"
              />
              <button type="submit" disabled={sending || !text.trim()} className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">
                Send
              </button>
            </form>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-gray-500">Select a friend to start chatting</p>
          </div>
        )}
      </div>
    </div>
  )
}
