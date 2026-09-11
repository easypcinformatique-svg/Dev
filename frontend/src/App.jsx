import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './shared/hooks/useAuthStore'
import LoginScreen from './pages/LoginScreen'
import PosScreen from './pages/pos/PosScreen'
import KitchenScreen from './pages/kitchen/KitchenScreen'
import DeliveryScreen from './pages/delivery/DeliveryScreen'
import AdminDashboard from './pages/admin/AdminDashboard'
import OnlineMenu from './pages/online/OnlineMenu'
import OnlineTrack from './pages/online/OnlineTrack'
import Layout from './shared/components/Layout'

export default function App() {
  const { user } = useAuthStore()

  return (
    <Routes>
      {/* Pages publiques */}
      <Route path="/commander" element={<OnlineMenu />} />
      <Route path="/suivi/:numero" element={<OnlineTrack />} />

      {/* Login */}
      <Route path="/login" element={<LoginScreen />} />

      {/* Pages authentifiees */}
      <Route element={user ? <Layout /> : <Navigate to="/login" />}>
        <Route path="/" element={<Navigate to="/pos" />} />
        <Route path="/pos" element={<PosScreen />} />
        <Route path="/cuisine" element={<KitchenScreen />} />
        <Route path="/livraisons" element={<DeliveryScreen />} />
        <Route path="/admin/*" element={<AdminDashboard />} />
      </Route>
    </Routes>
  )
}
