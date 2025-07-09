import { useQuery } from 'react-query'
import { FileText, Clock, CheckCircle, AlertTriangle, Users } from 'lucide-react'
import { ticketsAPI } from '../api/client'
import { useCurrentUser } from '../hooks/useAuth'
import LoadingSpinner from '../components/LoadingSpinner'

const Dashboard = () => {
  const user = useCurrentUser()
  
  const { data: dashboardData, isLoading, error } = useQuery(
    'dashboard-data',
    ticketsAPI.getDashboardData,
    {
      refetchInterval: 30000, // Обновляем каждые 30 секунд
    }
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

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center text-red-600">
          Ошибка загрузки данных дашборда
        </div>
      </div>
    )
  }

  const stats = dashboardData?.stats

  return (
    <div className="p-6 space-y-6">
      {/* Заголовок */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Добро пожаловать, {user?.full_name}!
        </h1>
        <p className="text-gray-600">
          Обзор ваших заявок и задач
        </p>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Всего заявок"
          value={stats?.total_tickets || 0}
          icon={FileText}
          color="blue"
        />
        <StatCard
          title="В ожидании"
          value={stats?.pending_tickets || 0}
          icon={Clock}
          color="yellow"
        />
        <StatCard
          title="В работе"
          value={stats?.in_progress_tickets || 0}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Выполнено"
          value={stats?.done_tickets || 0}
          icon={CheckCircle}
          color="green"
        />
      </div>

      {/* Среднее время выполнения */}
      {stats?.avg_completion_time_hours && (
        <div className="card">
          <div className="card-content">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Статистика выполнения
            </h3>
            <p className="text-2xl font-bold text-blue-600">
              {stats.avg_completion_time_hours} часов
            </p>
            <p className="text-sm text-gray-600">
              Среднее время выполнения заявки
            </p>
          </div>
        </div>
      )}

      {/* Последние заявки */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Последние заявки</h3>
        </div>
        <div className="card-content">
          {dashboardData?.recent_tickets?.length ? (
            <div className="space-y-4">
              {dashboardData.recent_tickets.slice(0, 5).map((ticket) => (
                <div key={ticket.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{ticket.title}</h4>
                    <p className="text-sm text-gray-600">{ticket.address}</p>
                    <div className="flex items-center mt-2 space-x-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full status-${ticket.status}`}>
                        {ticket.status}
                      </span>
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full priority-${ticket.priority}`}>
                        Приоритет {ticket.priority}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </p>
                    {ticket.executor && (
                      <p className="text-xs text-gray-500">
                        {ticket.executor.full_name}
                      </p>
                    )}
                  </div>
                </div>
              ))}
              
              <div className="text-center pt-4">
                <a href="/tickets" className="btn-outline">
                  Смотреть все заявки
                </a>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Заявок пока нет
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Создайте первую заявку для начала работы
              </p>
              <div className="mt-6">
                <a href="/tickets/new" className="btn-primary">
                  Создать заявку
                </a>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Мои задачи (для исполнителей) */}
      {user?.role === 'executor' && dashboardData?.my_tickets?.length && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Мои текущие задачи</h3>
          </div>
          <div className="card-content">
            <div className="space-y-4">
              {dashboardData.my_tickets.map((ticket) => (
                <div key={ticket.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{ticket.title}</h4>
                    <p className="text-sm text-gray-600">{ticket.address}</p>
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full status-${ticket.status} mt-2`}>
                      {ticket.status}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">
                      Дедлайн: {new Date(ticket.deadline).toLocaleDateString()}
                    </p>
                    <a href={`/tickets/${ticket.id}`} className="btn-sm btn-primary mt-2">
                      Открыть
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Компонент карточки статистики
const StatCard = ({ title, value, icon: Icon, color }: any) => {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  }

  return (
    <div className="card">
      <div className="card-content">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className={`p-3 rounded-md ${colorClasses[color]}`}>
              <Icon className="h-6 w-6 text-white" />
            </div>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd className="text-lg font-medium text-gray-900">
                {value}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard