import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const NAV = [
  { to: '/',                label: 'Home',             icon: '🏠' },
  { to: '/connect-spotify', label: 'Connect Spotify',  icon: '🎵' },
  { to: '/discover',        label: 'Discover Concerts', icon: '🎤' },
  { to: '/swipe',           label: 'Artist Swipe',     icon: '🎸' },
  { to: '/discovery',       label: 'Music Discovery',  icon: '✨' },
  { to: '/friends',         label: 'Friends',          icon: '👥' },
  { to: '/messages',        label: 'Messages',         icon: '💬' },
  { to: '/my-concerts',     label: 'My Concerts',      icon: '🎟️' },
]

export default function Layout({ children }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-56 flex-shrink-0 flex-col border-r border-white/10 bg-surface">
        <div className="px-4 py-5">
          <span className="text-lg font-bold text-white">🎸 The Setlist</span>
        </div>

        <nav className="flex-1 space-y-0.5 px-2">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-brand/20 text-brand font-medium'
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 px-4 py-4">
          <p className="truncate text-xs text-gray-500">{user?.email}</p>
          <button
            onClick={handleSignOut}
            className="mt-2 w-full rounded-lg px-3 py-1.5 text-left text-xs text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-base p-6">
        {children}
      </main>
    </div>
  )
}
