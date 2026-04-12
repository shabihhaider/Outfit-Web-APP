import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiMail, FiArrowLeft, FiCheck } from 'react-icons/fi'
import { forgotPassword } from '../api/auth.js'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await forgotPassword({ email })
      setSent(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-brand-50 dark:bg-brand-950">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md"
      >
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-sm text-brand-400 hover:text-brand-700 dark:hover:text-brand-200 mb-8 transition-colors"
        >
          <FiArrowLeft size={14} /> Back to login
        </Link>

        {sent ? (
          <div className="card p-8 text-center">
            <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-5">
              <FiCheck size={24} className="text-emerald-600 dark:text-emerald-400" />
            </div>
            <h2 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 mb-2">Check your email</h2>
            <p className="text-brand-500 dark:text-brand-400 text-sm leading-relaxed">
              If <span className="font-medium text-brand-700 dark:text-brand-300">{email}</span> is registered,
              you&apos;ll receive a reset link shortly. Check your spam folder if it doesn&apos;t arrive.
            </p>
            <Link to="/login" className="btn-primary inline-flex items-center justify-center mt-6 px-8 py-2.5">
              Return to login
            </Link>
          </div>
        ) : (
          <>
            <h2 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 mb-2">
              Forgot password?
            </h2>
            <p className="text-brand-500 dark:text-brand-400 mb-8">
              Enter your email and we&apos;ll send you a reset link.
            </p>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 p-3.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-sm"
              >
                {error}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
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
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3"
              >
                {loading ? <LoadingSpinner size="sm" /> : 'Send reset link'}
              </button>
            </form>
          </>
        )}
      </motion.div>
    </div>
  )
}
