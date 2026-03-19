import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

import Login from './pages/Login'
import Home from './pages/Home'
import ConnectSpotify from './pages/ConnectSpotify'
import DiscoverConcerts from './pages/DiscoverConcerts'
import ArtistSwipe from './pages/ArtistSwipe'
import MusicDiscovery from './pages/MusicDiscovery'
import Friends from './pages/Friends'
import Messages from './pages/Messages'
import MyConcerts from './pages/MyConcerts'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/"                element={<Home />} />
                <Route path="/connect-spotify" element={<ConnectSpotify />} />
                <Route path="/discover"        element={<DiscoverConcerts />} />
                <Route path="/swipe"           element={<ArtistSwipe />} />
                <Route path="/discovery"       element={<MusicDiscovery />} />
                <Route path="/friends"         element={<Friends />} />
                <Route path="/messages"        element={<Messages />} />
                <Route path="/my-concerts"     element={<MyConcerts />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
