import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { login } from '../api/auth.js'
import { useAuth } from '../context/AuthContext.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import { FiArrowRight, FiMail, FiLock, FiEye, FiEyeOff } from 'react-icons/fi'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { loginUser } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/dashboard'

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login({ email, password })
      setError('')
      loginUser(data.access_token, { name: data.name, email, id: data.user_id, gender: data.gender, avatar_url: data.avatar_url ?? null })
      const onboardingDone = localStorage.getItem('onboarding_done')
      setTimeout(() => {
        navigate(onboardingDone ? from : '/onboarding', { replace: true })
      }, 500)
    } catch (err) {
      console.error('Login error:', err)
      if (err.response?.status === 401) {
        setError('Invalid email or password. Please try again.')
      } else {
        setError(err.response?.data?.error || err.response?.data?.message || 'Connection error. Is the server running?')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: decorative panel */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-brand-900 dark:bg-brand-950 overflow-hidden">
        {/* Gradient orbs */}
        <div className="absolute top-1/4 -left-20 w-80 h-80 bg-accent-500/20 rounded-full blur-3xl animate-pulse-soft" />
        <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl animate-pulse-soft" style={{ animationDelay: '1.5s' }} />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div>
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center mb-8">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-white">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="font-display text-4xl xl:text-5xl font-bold text-white leading-tight">
              Your wardrobe,<br />
              <span className="text-accent-400 italic">reimagined.</span>
            </h2>
            <p className="mt-4 text-brand-400 text-lg max-w-md leading-relaxed">
              AI-powered outfit recommendations tailored to your style, occasion, and weather.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {['bg-accent-400', 'bg-emerald-400', 'bg-sky-400'].map((c, i) => (
                <div key={i} className={`w-8 h-8 rounded-full ${c} ring-2 ring-brand-900`} />
              ))}
            </div>
            <p className="text-sm text-brand-400">Trusted by fashion-forward users</p>
          </div>
        </div>
      </div>

      {/* Right: form — overflow-y-auto so short viewports can scroll */}
      <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center p-6 sm:p-8 py-12 bg-brand-50 dark:bg-brand-950">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex w-12 h-12 rounded-xl bg-brand-900 dark:bg-brand-100 items-center justify-center mb-4">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-white dark:text-brand-900">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h1 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100">
              Outfit<span className="text-accent-500">AI</span>
            </h1>
          </div>

          <div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-brand-900 dark:text-brand-100">
              Welcome back
            </h2>
            <p className="text-brand-500 dark:text-brand-400 mt-2">Sign in to your wardrobe</p>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-3.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-sm flex gap-2.5 items-start"
            >
              <span className="text-red-500 mt-0.5">!</span>
              <span>{error}</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-1.5">Email</label>
              <div className="relative">
                <FiMail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-400" size={16} />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-1.5">Password</label>
              <div className="relative">
                <FiLock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-400" size={16} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="input-field pl-10 pr-10"
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-brand-400 hover:text-brand-600 dark:hover:text-brand-200"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base group"
            >
              {loading ? (
                <LoadingSpinner size="sm" />
              ) : (
                <>
                  Sign In
                  <FiArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-brand-500 dark:text-brand-400">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 font-semibold transition-colors">
              Create one
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
