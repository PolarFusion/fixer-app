import axios, { AxiosResponse, AxiosError } from 'axios'
import toast from 'react-hot-toast'

// Типы данных
export interface User {
  id: number
  email: string
  full_name: string
  role: 'admin' | 'executor' | 'customer'
  is_active: boolean
  created_at: string
}

export interface Ticket {
  id: number
  title: string
  address: string
  description: string
  status: 'pending' | 'in_progress' | 'done' | 'rejected'
  priority: number
  deadline: string
  customer_id: number
  executor_id?: number
  created_at: string
  started_at?: string
  completed_at?: string
  completion_comment?: string
  rejection_reason?: string
  before_photo_path?: string
  after_photo_path?: string
  customer?: User
  executor?: User
}

export interface LoginRequest {
  username: string // email
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface TicketCreate {
  title: string
  address: string
  description: string
  deadline: string
  priority: number
  executor_id?: number
}

export interface DashboardData {
  stats: {
    total_tickets: number
    pending_tickets: number
    in_progress_tickets: number
    done_tickets: number
    rejected_tickets: number
    avg_completion_time_hours?: number
  }
  recent_tickets: Ticket[]
  my_tickets?: Ticket[]
}

// Базовый URL для API - используем внешний IP для демо
const getBaseURL = () => {
  // В продакшене используем относительные пути
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000'
  }
  // Для удаленного доступа используем внешний IP
  return 'http://52.32.147.109:8000'
}

// Создаем экземпляр axios
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Перехватчик запросов - добавляем токен авторизации
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Перехватчик ответов - обрабатываем ошибки
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Токен недействителен - выходим из системы
      localStorage.removeItem('access_token')
      window.location.href = '/login'
      toast.error('Сессия истекла. Войдите в систему заново.')
    } else if (error.response?.status === 403) {
      toast.error('У вас нет прав для выполнения этого действия')
    } else if (error.response?.status && error.response.status >= 500) {
      toast.error('Ошибка сервера. Попробуйте позже.')
    } else if (!error.response) {
      toast.error('Ошибка сети. Проверьте подключение к интернету.')
    }
    return Promise.reject(error)
  }
)

// ===== API МЕТОДЫ =====

// Аутентификация
export const authAPI = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const formData = new FormData()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)
    
    const response = await api.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/api/auth/me')
    return response.data
  },

  logout: () => {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  },
}

// Заявки
export const ticketsAPI = {
  getAll: async (params?: {
    status?: string
    executor_id?: number
    limit?: number
    offset?: number
  }): Promise<Ticket[]> => {
    const response = await api.get('/api/tickets/', { params })
    return response.data
  },

  getById: async (id: number): Promise<Ticket> => {
    const response = await api.get(`/api/tickets/${id}`)
    return response.data
  },

  create: async (data: TicketCreate): Promise<Ticket> => {
    const response = await api.post('/api/tickets/', data)
    return response.data
  },

  update: async (id: number, data: FormData): Promise<Ticket> => {
    const response = await api.put(`/api/tickets/${id}`, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/tickets/${id}`)
  },

  getExecutors: async (): Promise<Array<{id: number, full_name: string, email: string}>> => {
    const response = await api.get('/api/tickets/executors/list')
    return response.data
  },

  getDashboardData: async (): Promise<DashboardData> => {
    const response = await api.get('/api/tickets/dashboard/data')
    return response.data
  },
}

// Отчеты
export const reportsAPI = {
  downloadTicketReport: async (ticketId: number, format: 'pdf' | 'xlsx'): Promise<Blob> => {
    const response = await api.get(`/api/reports/${ticketId}`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  },

  downloadDigestReport: async (range: 'daily' | 'weekly', format: 'pdf' | 'xlsx'): Promise<Blob> => {
    const response = await api.get(`/api/reports/digest/${range}`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  },
}

// WebSocket для уведомлений
export class NotificationSocket {
  private ws: WebSocket | null = null
  private userId: number | null = null
  private reconnectInterval: number = 5000
  private maxReconnectAttempts: number = 10
  private reconnectAttempts: number = 0

  connect(userId: number) {
    this.userId = userId
    this.reconnectAttempts = 0
    this.createConnection()
  }

  private createConnection() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProtocol}//${window.location.host}/api/tickets/ws/${this.userId}`
      
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('🔌 WebSocket соединение установлено')
        this.reconnectAttempts = 0
        
        // Отправляем ping каждые 30 секунд
        setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send('ping')
          }
        }, 30000)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Ошибка парсинга WebSocket сообщения:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('🔌 WebSocket соединение закрыто')
        this.attemptReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('❌ Ошибка WebSocket:', error)
      }
    } catch (error) {
      console.error('❌ Ошибка создания WebSocket соединения:', error)
      this.attemptReconnect()
    }
  }

  private handleMessage(data: any) {
    if (data.type === 'ticket_updated') {
      // Показываем уведомление о изменении заявки
      const { action, ticket } = data
      let message = ''
      
      switch (action) {
        case 'created':
          message = `Создана новая заявка: ${ticket.title}`
          break
        case 'assigned':
          message = `Заявка назначена: ${ticket.title}`
          break
        case 'status_changed':
          message = `Изменен статус заявки: ${ticket.title}`
          break
        default:
          message = `Обновлена заявка: ${ticket.title}`
      }
      
      toast.success(message, {
        duration: 5000,
        position: 'top-right',
      })
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Превышено максимальное количество попыток переподключения')
      return
    }

    this.reconnectAttempts++
    console.log(`Попытка переподключения ${this.reconnectAttempts}/${this.maxReconnectAttempts}`)

    setTimeout(() => {
      this.createConnection()
    }, this.reconnectInterval)
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

// Экспорт экземпляра для использования в приложении
export const notificationSocket = new NotificationSocket()

export default api