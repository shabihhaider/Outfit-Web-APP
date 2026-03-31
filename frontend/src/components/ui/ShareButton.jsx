import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiShare2, FiLoader, FiCheck } from 'react-icons/fi'
import { shareOrDownload } from '../../utils/shareOutfit.js'

export default function ShareButton({ outfit, items, className = '', rounded = false }) {
  const [status, setStatus] = useState('idle') // idle, generating, success

  async function handleShare() {
    if (!outfit || !items?.length) return
    setStatus('generating')
    try {
      await shareOrDownload(outfit, items)
      setStatus('success')
      setTimeout(() => setStatus('idle'), 2000)
    } catch (err) {
      console.error('Share failed:', err)
      setStatus('idle')
    }
  }

  const isGenerating = status === 'generating'
  const isSuccess = status === 'success'

  if (rounded) {
    return (
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={handleShare}
        disabled={isGenerating}
        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm border ${
          isSuccess 
            ? 'bg-emerald-50 border-emerald-200 text-emerald-600 dark:bg-emerald-900/20 dark:border-emerald-800/40 dark:text-emerald-400' 
            : 'bg-white dark:bg-brand-800 border-brand-100 dark:border-brand-700 text-brand-500 hover:text-brand-900 dark:hover:text-brand-100'
        } ${className}`}
        title="Share or Download Composition"
      >
        <AnimatePresence mode="wait">
          {isGenerating ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <FiLoader size={16} className="animate-spin" />
            </motion.div>
          ) : isSuccess ? (
            <motion.div key="success" initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
              <FiCheck size={16} />
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <FiShare2 size={16} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    )
  }

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleShare}
      disabled={isGenerating}
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border ${
        isSuccess
          ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/10 dark:border-emerald-800/40 dark:text-emerald-400'
          : 'bg-brand-50/50 dark:bg-brand-800/20 border-brand-100/60 dark:border-brand-700/40 text-brand-500 hover:text-brand-900 dark:hover:text-brand-200'
      } disabled:opacity-50 ${className}`}
    >
      <AnimatePresence mode="wait">
        {isGenerating ? (
          <FiLoader size={12} className="animate-spin" />
        ) : isSuccess ? (
          <FiCheck size={12} />
        ) : (
          <FiShare2 size={12} />
        )}
      </AnimatePresence>
      <span>{isGenerating ? 'Sharing...' : isSuccess ? 'Shared' : 'Share'}</span>
    </motion.button>
  )
}
