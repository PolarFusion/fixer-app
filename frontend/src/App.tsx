import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './hooks/useAuth'
import { useEffect } from 'react'

// Страницы
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import TicketForm from './pages/TicketForm'
import TicketView from './pages/TicketView'

// Компоненты
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoadingSpinner from './components/LoadingSpinner'

function App() {
  const { user, isLoading, initializeAuth } = useAuthStore()

  // Инициализируем аутентификацию при загрузке приложения
  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  // Показываем загрузку пока проверяем токен
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner className="w-8 h-8 mx-auto mb-4" />
          <p className="text-gray-600">Загрузка приложения...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        {/* Публичные маршруты */}
        <Route
          path="/login"
          element={
            user ? <Navigate to="/dashboard" replace /> : <Login />
          }
        />

        {/* Защищенные маршруты */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          {/* Дашборд */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />

          {/* Заявки */}
          <Route path="tickets">
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="new" element={<TicketForm />} />
            <Route path=":id" element={<TicketView />} />
            <Route path=":id/edit" element={<TicketForm />} />
          </Route>

          {/* Пользователи (только для админов) */}
          <Route
            path="users"
            element={
              <ProtectedRoute requiredRole="admin">
                <div className="p-6">
                  <h1 className="text-2xl font-bold">Управление пользователями</h1>
                  <p className="text-gray-600 mt-2">Функционал в разработке</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Отчеты (для админов и исполнителей) */}
          <Route
            path="reports"
            element={
              <ProtectedRoute requiredRole={["admin", "executor"]}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold">Отчеты</h1>
                  <p className="text-gray-600 mt-2">Функционал в разработке</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Настройки */}
          <Route
            path="settings"
            element={
              <div className="p-6">
                <h1 className="text-2xl font-bold">Настройки</h1>
                <p className="text-gray-600 mt-2">Функционал в разработке</p>
              </div>
            }
          />
        </Route>

        {/* 404 страница */}
        <Route
          path="*"
          element={
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
                <p className="text-gray-600 mb-6">Страница не найдена</p>
                <a
                  href="/"
                  className="btn-primary"
                >
                  Вернуться на главную
                </a>
              </div>
            </div>
          }
        />
      </Routes>
    </div>
  )
}

export default App