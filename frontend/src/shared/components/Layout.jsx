import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuthStore'

const navItems = [
  { to: '/pos', label: 'Caisse', icon: '💰', roles: ['admin', 'caissier'] },
  { to: '/cuisine', label: 'Cuisine', icon: '👨‍🍳', roles: ['admin', 'pizzaiolo', 'caissier'] },
  { to: '/livraisons', label: 'Livraisons', icon: '🛵', roles: ['admin', 'caissier', 'livreur'] },
  { to: '/admin', label: 'Admin', icon: '⚙️', roles: ['admin'] },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleNav = navItems.filter((item) => item.roles.includes(user?.role))

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-20 bg-gray-800 flex flex-col items-center py-4 gap-2">
        <div className="text-2xl mb-4">🍕</div>
        {visibleNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center w-16 h-16 rounded-xl transition-colors
              ${isActive ? 'bg-pizza-500 text-white' : 'text-gray-400 hover:bg-gray-700 hover:text-white'}`
            }
          >
            <span className="text-xl">{item.icon}</span>
            <span className="text-[10px] mt-1">{item.label}</span>
          </NavLink>
        ))}
        <div className="mt-auto flex flex-col items-center gap-2">
          <div className="text-[10px] text-gray-500">{user?.nom}</div>
          <button
            onClick={handleLogout}
            className="w-12 h-12 rounded-lg bg-gray-700 hover:bg-red-600 text-gray-400 hover:text-white transition-colors flex items-center justify-center"
          >
            ⏻
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
