import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth, useCurrentUser } from '../hooks/useAuth'

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: string | string[]
}

const ProtectedRoute = ({ children, requiredRole }: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading } = useAuth()
  const user = useCurrentUser()

  // Показываем загрузку пока проверяем аутентификацию
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner w-8 h-8" />
      </div>
    )
  }

  // Если не аутентифицирован - перенаправляем на логин
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  // Проверяем требуемую роль
  if (requiredRole) {
    const allowedRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole]
    
    if (!allowedRoles.includes(user.role)) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Доступ запрещен</h1>
            <p className="text-gray-600 mb-6">У вас нет прав для просмотра этой страницы</p>
            <a href="/dashboard" className="btn-primary">
              Вернуться на главную
            </a>
          </div>
        </div>
      )
    }
  }

  return <>{children}</>
}

export default ProtectedRoute