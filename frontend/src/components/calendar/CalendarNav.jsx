import { motion } from 'framer-motion'
import { FiChevronLeft, FiChevronRight } from 'react-icons/fi'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function CalendarNav({ year, month, onChange }) {
  function prev() {
    if (month === 0) onChange(year - 1, 11)
    else onChange(year, month - 1)
  }

  function next() {
    if (month === 11) onChange(year + 1, 0)
    else onChange(year, month + 1)
  }

  function goToday() {
    const now = new Date()
    onChange(now.getFullYear(), now.getMonth())
  }

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-3">
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={prev}
          className="p-2 rounded-xl border border-brand-200/60 dark:border-brand-700/40 text-brand-600 dark:text-brand-400 hover:bg-brand-100/60 dark:hover:bg-brand-800/30 transition-colors"
          title="Previous month"
        >
          <FiChevronLeft size={18} />
        </motion.button>
        <h2 className="font-display text-2xl sm:text-3xl font-bold text-brand-900 dark:text-brand-100 min-w-[200px] text-center tracking-tight">
          {MONTH_NAMES[month]} {year}
        </h2>
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={next}
          className="p-2 rounded-xl border border-brand-200/60 dark:border-brand-700/40 text-brand-600 dark:text-brand-400 hover:bg-brand-100/60 dark:hover:bg-brand-800/30 transition-colors"
          title="Next month"
        >
          <FiChevronRight size={18} />
        </motion.button>
      </div>
      <button onClick={goToday} className="btn-secondary text-sm px-3.5 py-1.5 rounded-xl">
        Today
      </button>
    </div>
  )
}
