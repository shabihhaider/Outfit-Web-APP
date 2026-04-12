import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { register, login } from '../api/auth.js'
import { useAuth } from '../context/AuthContext.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import { FiArrowRight, FiUser, FiMail, FiLock, FiEye, FiEyeOff } from 'react-icons/fi'

const GENDERS = ['men', 'women', 'unisex']

export default function RegisterPage() {
  const [form, setForm] = useState({ name: '', email: '', password: '', gender: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { loginUser } = useAuth()
  const navigate = useNavigate()

  function update(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.gender) { setError('Please select a style preference.'); return }
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      await register(form)
      const data = await login({ email: form.email, password: form.password })
      setError('')
      loginUser(data.access_token, { name: form.name, email: form.email, id: data.user_id, gender: form.gender })
      navigate('/onboarding', { replace: true })
    } catch (err) {
      console.error('Registration error:', err)
      setError(err.response?.data?.error || err.response?.data?.message || 'Registration failed. Please check your details.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: decorative panel */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-brand-900 dark:bg-brand-950 overflow-hidden">
        <div className="absolute top-1/3 left-1/4 w-80 h-80 bg-accent-500/15 rounded-full blur-3xl animate-pulse-soft" />
        <div className="absolute bottom-1/3 -right-10 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse-soft" style={{ animationDelay: '2s' }} />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div>
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center mb-8">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-white">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="font-display text-4xl xl:text-5xl font-bold text-white leading-tight">
              Build your<br />
              <span className="text-accent-400 italic">perfect wardrobe.</span>
            </h2>
            <p className="mt-4 text-brand-400 text-lg max-w-md leading-relaxed">
              Upload your clothes. Let AI understand your style. Get outfits that work.
            </p>
          </div>

          <div className="space-y-3">
            {['AI category detection', 'Weather-aware recommendations', '3-occasion scoring engine'].map((feature, i) => (
              <div key={i} className="flex items-center gap-3 text-brand-300 text-sm">
                <div className="w-5 h-5 rounded-full bg-accent-500/20 flex items-center justify-center flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-accent-400" />
                </div>
                {feature}
              </div>
            ))}
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
          </div>

          <div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-brand-900 dark:text-brand-100">
              Create account
            </h2>
            <p className="text-brand-500 dark:text-brand-400 mt-2">Set up your smart wardrobe</p>
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
              <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-1.5">Full Name</label>
              <div className="relative">
                <FiUser className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-400" size={16} />
                <input type="text" value={form.name} onChange={update('name')} className="input-field pl-10" placeholder="Your name" required />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-1.5">Email</label>
              <div className="relative">
                <FiMail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-400" size={16} />
                <input type="email" value={form.email} onChange={update('email')} className="input-field pl-10" placeholder="you@example.com" required autoComplete="email" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-1.5">Password</label>
              <div className="relative">
                <FiLock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-400" size={16} />
                <input type={showPassword ? 'text' : 'password'} value={form.password} onChange={update('password')} className="input-field pl-10 pr-10" placeholder="Min. 8 characters" required autoComplete="new-password" />
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
            <div>
              <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-2">Style preference</label>
              <div className="flex gap-2">
                {GENDERS.map(g => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setForm(f => ({ ...f, gender: g }))}
                    className={`flex-1 py-2.5 rounded-xl text-sm font-medium border-2 transition-all duration-200 ${
                      form.gender === g
                        ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100 shadow-md'
                        : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400 dark:hover:border-brand-500'
                    }`}
                  >
                    {g.charAt(0).toUpperCase() + g.slice(1)}
                  </button>
                ))}
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
                  Create Account
                  <FiArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-brand-500 dark:text-brand-400">
            Already have an account?{' '}
            <Link to="/login" className="text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 font-semibold transition-colors">
              Sign In
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
