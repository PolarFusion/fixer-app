import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { LogIn, User, Lock, AlertCircle } from 'lucide-react'
import { useAuthStore } from '../hooks/useAuth'
import LoadingSpinner from '../components/LoadingSpinner'

interface LoginForm {
  email: string
  password: string
}

const Login = () => {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginForm>()

  const onSubmit = async (data: LoginForm) => {
    try {
      setIsSubmitting(true)
      await login({
        username: data.email,
        password: data.password,
      })
      navigate('/dashboard')
    } catch (error: any) {
      // Ошибки уже обработаны в useAuthStore
      setError('root', {
        message: 'Ошибка входа в систему',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-md w-full space-y-8 p-8">
        {/* Заголовок */}
        <div className="text-center">
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-primary-100">
            <LogIn className="h-6 w-6 text-primary-600" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Вход в систему
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Система управления ремонтно-монтажными заявками
          </p>
        </div>

        {/* Форма входа */}
        <div className="card">
          <div className="card-content">
            <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
              {/* Email */}
              <div>
                <label htmlFor="email" className="form-label">
                  Email адрес
                </label>
                <div className="mt-1 relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <input
                    {...register('email', {
                      required: 'Email обязателен',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Неверный формат email',
                      },
                    })}
                    type="email"
                    autoComplete="email"
                    className={`form-input pl-10 ${
                      errors.email ? 'border-red-500' : ''
                    }`}
                    placeholder="Введите ваш email"
                    disabled={isSubmitting}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.email.message}
                  </p>
                )}
              </div>

              {/* Пароль */}
              <div>
                <label htmlFor="password" className="form-label">
                  Пароль
                </label>
                <div className="mt-1 relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <input
                    {...register('password', {
                      required: 'Пароль обязателен',
                      minLength: {
                        value: 6,
                        message: 'Пароль должен содержать минимум 6 символов',
                      },
                    })}
                    type="password"
                    autoComplete="current-password"
                    className={`form-input pl-10 ${
                      errors.password ? 'border-red-500' : ''
                    }`}
                    placeholder="Введите ваш пароль"
                    disabled={isSubmitting}
                  />
                </div>
                {errors.password && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {/* Ошибка формы */}
              {errors.root && (
                <div className="rounded-md bg-red-50 border border-red-200 p-4">
                  <div className="flex">
                    <AlertCircle className="h-5 w-5 text-red-400" />
                    <div className="ml-3">
                      <p className="text-sm text-red-800">
                        {errors.root.message}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Кнопка входа */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary w-full"
              >
                {isSubmitting ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Вход...
                  </>
                ) : (
                  'Войти'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Тестовые данные */}
        <div className="card">
          <div className="card-content">
            <h3 className="text-sm font-medium text-gray-900 mb-3">
              Тестовые учетные данные:
            </h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div>
                <strong>Администратор:</strong> admin1@company.com / admin123
              </div>
              <div>
                <strong>Исполнитель:</strong> executor1@company.com / exec123
              </div>
              <div>
                <strong>Клиент:</strong> customer1@gmail.com / customer123
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login