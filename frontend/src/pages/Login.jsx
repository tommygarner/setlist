import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const { signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', username: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const { error } = await signIn(form.email, form.password)
    setLoading(false)
    if (error) return setError(error.message)
    navigate('/')
  }

  const handleSignUp = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) return setError('Passwords do not match')
    if (form.password.length < 6) return setError('Password must be at least 6 characters')
    setLoading(true)
    const { error } = await signUp(form.email, form.password, form.username)
    setLoading(false)
    if (error) return setError(error.message)
    setError('')
    alert('Account created! Check your email to verify.')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-2 text-center text-3xl font-bold text-white">🎸 The Setlist</h1>
        <p className="mb-8 text-center text-sm text-gray-400">Discover concerts you'll love</p>

        <div className="mb-6 flex rounded-lg bg-surface p-1">
          {['login', 'signup'].map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError('') }}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                tab === t ? 'bg-brand text-black' : 'text-gray-400 hover:text-white'
              }`}
            >
              {t === 'login' ? 'Log in' : 'Sign up'}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {tab === 'login' ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <input
              type="email" placeholder="Email" value={form.email} onChange={set('email')} required
              className="w-full rounded-lg bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 outline-none ring-1 ring-white/10 focus:ring-brand"
            />
            <input
              type="password" placeholder="Password" value={form.password} onChange={set('password')} required
              className="w-full rounded-lg bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 outline-none ring-1 ring-white/10 focus:ring-brand"
            />
            <button
              type="submit" disabled={loading}
              className="w-full rounded-lg bg-brand py-3 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Log in'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSignUp} className="space-y-4">
            <input
              type="text" placeholder="Username" value={form.username} onChange={set('username')} required
              className="w-full rounded-lg bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 outline-none ring-1 ring-white/10 focus:ring-brand"
            />
            <input
              type="email" placeholder="Email" value={form.email} onChange={set('email')} required
              className="w-full rounded-lg bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 outline-none ring-1 ring-white/10 focus:ring-brand"
            />
            <input
              type="password" placeholder="Password" value={form.password} onChange={set('password')} required
              className="w-full rounded-lg bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 outline-none ring-1 ring-white/10 focus:ring-brand"
            />
            <input
              type="password" placeholder="Confirm password" value={form.confirm} onChange={set('confirm')} required
              className="w-full rounded-lg bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 outline-none ring-1 ring-white/10 focus:ring-brand"
            />
            <button
              type="submit" disabled={loading}
              className="w-full rounded-lg bg-brand py-3 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
