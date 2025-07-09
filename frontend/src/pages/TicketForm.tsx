import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation } from 'react-query'
import toast from 'react-hot-toast'
import { ticketsAPI } from '../api/client'
import { useCurrentUser } from '../hooks/useAuth'
import LoadingSpinner from '../components/LoadingSpinner'

interface TicketFormData {
  title: string
  address: string
  description: string
  deadline: string
  priority: number
  executor_id?: number
}

const TicketForm = () => {
  const navigate = useNavigate()
  const { id } = useParams()
  const user = useCurrentUser()
  const isEdit = !!id

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<TicketFormData>()

  // Загружаем данные заявки для редактирования
  const { data: ticket, isLoading: ticketLoading } = useQuery(
    ['ticket', id],
    () => ticketsAPI.getById(Number(id)),
    { enabled: !!id }
  )

  // Загружаем список исполнителей
  const { data: executors } = useQuery('executors', ticketsAPI.getExecutors)

  // Мутация для создания/обновления
  const createMutation = useMutation(ticketsAPI.create)
  const updateMutation = useMutation(({ id, data }: { id: number, data: FormData }) => 
    ticketsAPI.update(id, data)
  )

  // Заполняем форму при редактировании
  useEffect(() => {
    if (ticket && isEdit) {
      setValue('title', ticket.title)
      setValue('address', ticket.address)
      setValue('description', ticket.description)
      setValue('deadline', ticket.deadline.split('T')[0])
      setValue('priority', ticket.priority)
      setValue('executor_id', ticket.executor_id)
    }
  }, [ticket, isEdit, setValue])

  const onSubmit = async (data: TicketFormData) => {
    try {
      if (isEdit && ticket) {
        const formData = new FormData()
        Object.entries(data).forEach(([key, value]) => {
          if (value !== undefined) {
            formData.append(key, String(value))
          }
        })
        
        await updateMutation.mutateAsync({ id: ticket.id, data: formData })
        toast.success('Заявка обновлена')
      } else {
        await createMutation.mutateAsync({
          ...data,
          deadline: new Date(data.deadline).toISOString(),
        })
        toast.success('Заявка создана')
      }
      
      navigate('/dashboard')
    } catch (error) {
      toast.error('Ошибка сохранения заявки')
    }
  }

  if (ticketLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? 'Редактировать заявку' : 'Создать заявку'}
        </h1>
      </div>

      <div className="card">
        <div className="card-content">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Заголовок */}
            <div>
              <label className="form-label">Заголовок заявки</label>
              <input
                {...register('title', { required: 'Заголовок обязателен' })}
                type="text"
                className="form-input"
                placeholder="Краткое описание проблемы"
              />
              {errors.title && <p className="form-error">{errors.title.message}</p>}
            </div>

            {/* Адрес */}
            <div>
              <label className="form-label">Адрес</label>
              <input
                {...register('address', { required: 'Адрес обязателен' })}
                type="text"
                className="form-input"
                placeholder="Адрес выполнения работ"
              />
              {errors.address && <p className="form-error">{errors.address.message}</p>}
            </div>

            {/* Описание */}
            <div>
              <label className="form-label">Описание работ</label>
              <textarea
                {...register('description', { required: 'Описание обязательно' })}
                className="form-textarea"
                rows={4}
                placeholder="Подробное описание необходимых работ"
              />
              {errors.description && <p className="form-error">{errors.description.message}</p>}
            </div>

            {/* Дедлайн */}
            <div>
              <label className="form-label">Крайний срок</label>
              <input
                {...register('deadline', { required: 'Крайний срок обязателен' })}
                type="date"
                className="form-input"
                min={new Date().toISOString().split('T')[0]}
              />
              {errors.deadline && <p className="form-error">{errors.deadline.message}</p>}
            </div>

            {/* Приоритет */}
            <div>
              <label className="form-label">Приоритет</label>
              <select {...register('priority')} className="form-select">
                <option value={1}>1 - Низкий</option>
                <option value={2}>2 - Обычный</option>
                <option value={3}>3 - Высокий</option>
                <option value={4}>4 - Критический</option>
                <option value={5}>5 - Экстренный</option>
              </select>
            </div>

            {/* Исполнитель (только для админов) */}
            {user?.role === 'admin' && executors && (
              <div>
                <label className="form-label">Исполнитель</label>
                <select {...register('executor_id')} className="form-select">
                  <option value="">Не назначен</option>
                  {executors.map((executor) => (
                    <option key={executor.id} value={executor.id}>
                      {executor.full_name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Кнопки */}
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="btn-outline"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={createMutation.isLoading || updateMutation.isLoading}
                className="btn-primary"
              >
                {createMutation.isLoading || updateMutation.isLoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Сохранение...
                  </>
                ) : (
                  isEdit ? 'Обновить' : 'Создать'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default TicketForm