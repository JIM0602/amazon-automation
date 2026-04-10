import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User as UserIcon, Lock, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      setError('请输入用户名和密码')
      return
    }

    try {
      setIsLoading(true)
      setError('')
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError('用户名或密码错误')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#0a0a1a] to-[var(--color-primary)]">
      <div className="glass p-8 md:p-12 rounded-2xl w-full max-w-md animate-fade-in shadow-2xl">
        <div className="text-center mb-8 animate-slide-up">
          <h1 className="text-3xl font-bold text-white mb-2 tracking-wider">PUDIWIND AI</h1>
          <p className="text-gray-300 text-sm opacity-80">Amazon 智能运营平台</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <UserIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="用户名"
                className="w-full pl-11 pr-4 py-3 bg-[var(--color-surface)] border border-[var(--color-glass-border)] rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent transition-all"
                disabled={isLoading}
              />
            </div>

            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="密码"
                className="w-full pl-11 pr-4 py-3 bg-[var(--color-surface)] border border-[var(--color-glass-border)] rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent transition-all"
                disabled={isLoading}
              />
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm text-center bg-red-400/10 py-2 rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 px-4 bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-primary-light)] hover:from-blue-500 hover:to-blue-400 text-white font-medium rounded-xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0a0a1a] focus:ring-[var(--color-accent)] transition-all flex items-center justify-center shadow-lg"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              '登录'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}