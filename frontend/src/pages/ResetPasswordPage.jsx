import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiLock, FiEye, FiEyeOff, FiCheck } from 'react-icons/fi'
import { resetPassword } from '../api/auth.js'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setLoading(true)
    try {
      await resetPassword({ token, password })
      setDone(true)
      setTimeout(() => navigate('/login', { replace: true }), 3000)
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid or expired reset link. Please request a new one.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-brand-50 dark:bg-brand-950">
        <div className="card p-8 text-center max-w-md w-full">
          <p className="text-brand-500 dark:text-brand-400 mb-4">Invalid reset link.</p>
          <Link to="/forgot-password" className="btn-primary inline-flex items-center justify-center px-6 py-2.5">
            Request a new link
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-brand-50 dark:bg-brand-950">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md"
      >
        {done ? (
          <div className="card p-8 text-center">
            <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-5">
              <FiCheck size={24} className="text-emerald-600 dark:text-emerald-400" />
            </div>
            <h2 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 mb-2">Password updated!</h2>
            <p className="text-brand-500 dark:text-brand-400 text-sm">Redirecting you to login…</p>
          </div>
        ) : (
          <>
            <h2 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 mb-2">
              Set new password
            </h2>
            <p className="text-brand-500 dark:text-brand-400 mb-8">
              Choose a strong password for your account.
            </p>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 p-3.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-sm"
              >
                {error}{' '}
                {error.includes('expired') && (
                  <Link to="/forgot-password" className="underline font-medium">Request a new link</Link>
                )}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-1.5">New password</label>
                <div className="relative">
                  <FiLock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-500" size={16} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="input-field pl-10 pr-10"
                    placeholder="Min. 8 characters"
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-brand-500 hover:text-brand-600 dark:hover:text-brand-200"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
                  </button>
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3"
              >
                {loading ? <LoadingSpinner size="sm" /> : 'Reset password'}
              </button>
            </form>
          </>
        )}
      </motion.div>
    </div>
  )
}
