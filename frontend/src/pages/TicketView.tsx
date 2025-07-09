import { useParams } from 'react-router-dom'
import { useQuery } from 'react-query'
import { FileText, MapPin, Calendar, User, Clock } from 'lucide-react'
import { ticketsAPI } from '../api/client'
import { useCurrentUser } from '../hooks/useAuth'
import LoadingSpinner from '../components/LoadingSpinner'

const TicketView = () => {
  const { id } = useParams()
  const user = useCurrentUser()

  const { data: ticket, isLoading, error } = useQuery(
    ['ticket', id],
    () => ticketsAPI.getById(Number(id)),
    { enabled: !!id }
  )

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div className="p-6">
        <div className="text-center text-red-600">
          Заявка не найдена
        </div>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'status-pending'
      case 'in_progress': return 'status-in_progress'
      case 'done': return 'status-done'
      case 'rejected': return 'status-rejected'
      default: return 'bg-gray-100'
    }
  }

  const getPriorityColor = (priority: number) => {
    return `priority-${priority}`
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Заголовок */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {ticket.title}
            </h1>
            <div className="flex items-center space-x-4">
              <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(ticket.status)}`}>
                {ticket.status}
              </span>
              <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${getPriorityColor(ticket.priority)}`}>
                Приоритет {ticket.priority}
              </span>
            </div>
          </div>
          <div className="flex space-x-2">
            <button className="btn-outline">
              Скачать PDF
            </button>
            {(user?.role === 'admin' || ticket.executor_id === user?.id) && (
              <a href={`/tickets/${ticket.id}/edit`} className="btn-primary">
                Редактировать
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Основная информация */}
        <div className="lg:col-span-2 space-y-6">
          {/* Детали заявки */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Детали заявки</h3>
            </div>
            <div className="card-content space-y-4">
              <div className="flex items-start space-x-3">
                <MapPin className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Адрес</p>
                  <p className="text-gray-600">{ticket.address}</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <FileText className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Описание работ</p>
                  <p className="text-gray-600 whitespace-pre-wrap">{ticket.description}</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <Calendar className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Крайний срок</p>
                  <p className="text-gray-600">
                    {new Date(ticket.deadline).toLocaleDateString('ru-RU')}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Фотографии */}
          {(ticket.before_photo_path || ticket.after_photo_path) && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Фотографии</h3>
              </div>
              <div className="card-content">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {ticket.before_photo_path && (
                    <div>
                      <p className="text-sm font-medium text-gray-900 mb-2">До выполнения</p>
                      <img
                        src={`/media/${ticket.before_photo_path.split('/').pop()}`}
                        alt="До выполнения"
                        className="w-full h-48 object-cover rounded-lg border"
                      />
                    </div>
                  )}
                  {ticket.after_photo_path && (
                    <div>
                      <p className="text-sm font-medium text-gray-900 mb-2">После выполнения</p>
                      <img
                        src={`/media/${ticket.after_photo_path.split('/').pop()}`}
                        alt="После выполнения"
                        className="w-full h-48 object-cover rounded-lg border"
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Комментарии */}
          {(ticket.completion_comment || ticket.rejection_reason) && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Комментарии</h3>
              </div>
              <div className="card-content">
                {ticket.completion_comment && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm font-medium text-green-900 mb-1">
                      Комментарий о выполнении
                    </p>
                    <p className="text-green-800">{ticket.completion_comment}</p>
                  </div>
                )}
                {ticket.rejection_reason && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm font-medium text-red-900 mb-1">
                      Причина отклонения
                    </p>
                    <p className="text-red-800">{ticket.rejection_reason}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Боковая панель */}
        <div className="space-y-6">
          {/* Участники */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Участники</h3>
            </div>
            <div className="card-content space-y-4">
              <div className="flex items-center space-x-3">
                <User className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Заказчик</p>
                  <p className="text-gray-600">{ticket.customer?.full_name}</p>
                </div>
              </div>
              
              {ticket.executor && (
                <div className="flex items-center space-x-3">
                  <User className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Исполнитель</p>
                    <p className="text-gray-600">{ticket.executor.full_name}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Временная информация */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Временная информация</h3>
            </div>
            <div className="card-content space-y-4">
              <div className="flex items-center space-x-3">
                <Clock className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Создана</p>
                  <p className="text-gray-600">
                    {new Date(ticket.created_at).toLocaleString('ru-RU')}
                  </p>
                </div>
              </div>
              
              {ticket.started_at && (
                <div className="flex items-center space-x-3">
                  <Clock className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Начата</p>
                    <p className="text-gray-600">
                      {new Date(ticket.started_at).toLocaleString('ru-RU')}
                    </p>
                  </div>
                </div>
              )}
              
              {ticket.completed_at && (
                <div className="flex items-center space-x-3">
                  <Clock className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Завершена</p>
                    <p className="text-gray-600">
                      {new Date(ticket.completed_at).toLocaleString('ru-RU')}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Действия для исполнителей */}
          {user?.role === 'executor' && ticket.executor_id === user.id && ticket.status === 'in_progress' && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Действия</h3>
              </div>
              <div className="card-content space-y-3">
                <button className="btn-success w-full">
                  Завершить работу
                </button>
                <button className="btn-danger w-full">
                  Отклонить заявку
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TicketView