import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { 
  Home, 
  FileText, 
  Users, 
  BarChart3, 
  Settings, 
  LogOut, 
  Menu,
  X
} from 'lucide-react'
import { useAuthStore, useCurrentUser, useIsAdmin } from '../hooks/useAuth'

const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const logout = useAuthStore((state) => state.logout)
  const user = useCurrentUser()
  const isAdmin = useIsAdmin()

  const navigation = [
    { name: 'Дашборд', href: '/dashboard', icon: Home },
    { name: 'Создать заявку', href: '/tickets/new', icon: FileText },
    ...(isAdmin ? [{ name: 'Пользователи', href: '/users', icon: Users }] : []),
    { name: 'Отчеты', href: '/reports', icon: BarChart3 },
    { name: 'Настройки', href: '/settings', icon: Settings },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Мобильное меню */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
          
          <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white">
            <div className="absolute top-0 right-0 -mr-12 pt-2">
              <button
                type="button"
                className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                onClick={() => setSidebarOpen(false)}
              >
                <X className="h-6 w-6 text-white" />
              </button>
            </div>
            
            <SidebarContent navigation={navigation} user={user} logout={logout} />
          </div>
        </div>
      )}

      {/* Десктопный сайдбар */}
      <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
        <SidebarContent navigation={navigation} user={user} logout={logout} />
      </div>

      {/* Основной контент */}
      <div className="flex-1 md:pl-64 flex flex-col">
        {/* Верхняя панель */}
        <div className="sticky top-0 z-10 md:hidden pl-1 pt-1 sm:pl-3 sm:pt-3 bg-gray-50">
          <button
            type="button"
            className="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
        </div>

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

// Компонент содержимого сайдбара
const SidebarContent = ({ navigation, user, logout }: any) => {
  return (
    <div className="flex-1 flex flex-col bg-white border-r border-gray-200">
      {/* Логотип */}
      <div className="flex-shrink-0 flex items-center px-4 py-4 border-b border-gray-200">
        <h1 className="text-lg font-semibold text-gray-900">
          Ремонт-Сервис
        </h1>
      </div>

      {/* Навигация */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navigation.map((item: any) => (
          <a
            key={item.name}
            href={item.href}
            className="group flex items-center px-2 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          >
            <item.icon className="mr-3 h-5 w-5" />
            {item.name}
          </a>
        ))}
      </nav>

      {/* Профиль пользователя */}
      <div className="flex-shrink-0 border-t border-gray-200 p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
              <span className="text-sm font-medium text-gray-700">
                {user?.full_name?.charAt(0).toUpperCase()}
              </span>
            </div>
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
            <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
          </div>
          <button
            onClick={logout}
            className="ml-3 inline-flex items-center p-1 rounded-md text-gray-400 hover:text-gray-500"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default Layout