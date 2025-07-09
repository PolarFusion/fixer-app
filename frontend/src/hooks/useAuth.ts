import { create } from 'zustand'
import { authAPI, notificationSocket, type User, type LoginRequest } from '../api/client'
import toast from 'react-hot-toast'

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  
  // Действия
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
  initializeAuth: () => Promise<void>
  setUser: (user: User | null) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (credentials: LoginRequest) => {
    try {
      set({ isLoading: true })
      
      // Выполняем логин
      const loginResponse = await authAPI.login(credentials)
      
      // Сохраняем токен
      localStorage.setItem('access_token', loginResponse.access_token)
      
      // Получаем данные пользователя
      const user = await authAPI.getCurrentUser()
      
      set({ 
        user,
        isAuthenticated: true,
        isLoading: false 
      })
      
      // Подключаемся к WebSocket для уведомлений
      notificationSocket.connect(user.id)
      
      toast.success(`Добро пожаловать, ${user.full_name}!`)
      
    } catch (error: any) {
      set({ isLoading: false })
      
      // Обрабатываем ошибки входа
      if (error.response?.status === 401) {
        toast.error('Неверный email или пароль')
      } else {
        toast.error('Ошибка входа в систему')
      }
      
      throw error
    }
  },

  logout: () => {
    // Очищаем токен и состояние
    localStorage.removeItem('access_token')
    notificationSocket.disconnect()
    
    set({ 
      user: null,
      isAuthenticated: false,
      isLoading: false 
    })
    
    toast.success('Вы успешно вышли из системы')
    
    // Перенаправляем на страницу входа
    window.location.href = '/login'
  },

  initializeAuth: async () => {
    try {
      const token = localStorage.getItem('access_token')
      
      if (!token) {
        set({ isLoading: false, isAuthenticated: false })
        return
      }
      
      // Проверяем токен, получая данные пользователя
      const user = await authAPI.getCurrentUser()
      
      set({ 
        user,
        isAuthenticated: true,
        isLoading: false 
      })
      
      // Подключаемся к WebSocket
      notificationSocket.connect(user.id)
      
    } catch (error) {
      // Токен недействителен - очищаем его
      localStorage.removeItem('access_token')
      set({ 
        user: null,
        isAuthenticated: false,
        isLoading: false 
      })
    }
  },

  setUser: (user: User | null) => {
    set({ 
      user,
      isAuthenticated: !!user 
    })
  },
}))

// Хелпер хуки для удобства
export const useAuth = () => {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  return { user, isAuthenticated, isLoading }
}

export const useCurrentUser = () => {
  return useAuthStore((state) => state.user)
}

export const useIsAdmin = () => {
  const user = useCurrentUser()
  return user?.role === 'admin'
}

export const useIsExecutor = () => {
  const user = useCurrentUser()
  return user?.role === 'executor'
}

export const useIsCustomer = () => {
  const user = useCurrentUser()
  return user?.role === 'customer'
}

export const useCanCreateTickets = () => {
  const user = useCurrentUser()
  return user?.role === 'customer' || user?.role === 'admin'
}

export const useCanManageUsers = () => {
  const user = useCurrentUser()
  return user?.role === 'admin'
}

export const useCanGenerateReports = () => {
  const user = useCurrentUser()
  return user?.role === 'admin' || user?.role === 'executor'
}