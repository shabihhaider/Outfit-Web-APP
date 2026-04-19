import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiArrowRight } from 'react-icons/fi'

export default function NotFoundPage() {
  useEffect(() => {
    const prev = document.title
    document.title = '404 — Page Not Found | OutfitAI'
    return () => { document.title = prev }
  }, [])

  return (
    <div className="min-h-screen bg-brand-50 dark:bg-brand-950 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="text-center max-w-sm"
      >
        <p className="font-mono text-7xl font-bold text-accent-500 mb-4 select-none">404</p>
        <h1 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200 mb-2">
          Page not found
        </h1>
        <p className="text-sm text-brand-400 dark:text-brand-500 mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 btn-accent px-5 py-2.5 rounded-xl text-sm font-medium"
        >
          Go to Dashboard
          <FiArrowRight size={14} />
        </Link>
      </motion.div>
    </div>
  )
}
