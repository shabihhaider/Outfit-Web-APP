import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiThumbsUp, FiThumbsDown, FiCheck } from 'react-icons/fi'
import { submitFeedback } from '../../api/outfits.js'

export default function FeedbackButtons({ historyId }) {
  const [voted, setVoted] = useState(null)

  const mutation = useMutation({
    mutationFn: (rating) => submitFeedback(historyId, { rating }),
  })

  function handleVote(rating) {
    if (voted || !historyId) return
    setVoted(rating)
    mutation.mutate(rating)
  }

  if (!historyId) return null

  return (
    <div className="flex items-center gap-2.5">
      <span className="text-[11px] text-brand-400 dark:text-brand-500">Rate:</span>
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => handleVote(1)}
        disabled={!!voted}
        className={`p-1.5 rounded-lg transition-all ${
          voted === 1
            ? 'bg-emerald-100/80 dark:bg-emerald-900/25 text-emerald-600 dark:text-emerald-400'
            : 'text-brand-400 dark:text-brand-500 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/15'
        }`}
        title="Good outfit"
      >
        <FiThumbsUp size={14} />
      </motion.button>
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => handleVote(-1)}
        disabled={!!voted}
        className={`p-1.5 rounded-lg transition-all ${
          voted === -1
            ? 'bg-red-100/80 dark:bg-red-900/25 text-red-500 dark:text-red-400'
            : 'text-brand-400 dark:text-brand-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/15'
        }`}
        title="Not my style"
      >
        <FiThumbsDown size={14} />
      </motion.button>
      {voted && (
        <motion.span
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-[11px] text-brand-400 dark:text-brand-500 flex items-center gap-0.5"
        >
          <FiCheck size={12} /> Thanks
        </motion.span>
      )}
    </div>
  )
}
