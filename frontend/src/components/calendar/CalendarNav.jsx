import { motion } from 'framer-motion'
import { FiChevronLeft, FiChevronRight, FiCalendar, FiGrid } from 'react-icons/fi'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const SHORT_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatWeekLabel(weekStart) {
  const end = new Date(weekStart)
  end.setDate(end.getDate() + 6)
  const startM = SHORT_MONTHS[weekStart.getMonth()]
  const endM   = SHORT_MONTHS[end.getMonth()]
  const sameMonth = weekStart.getMonth() === end.getMonth()
  const year = end.getFullYear()
  return sameMonth
    ? `${startM} ${weekStart.getDate()} – ${end.getDate()}, ${year}`
    : `${startM} ${weekStart.getDate()} – ${endM} ${end.getDate()}, ${year}`
}

// Exported for CalendarPage — not a component, lives here to avoid a separate utils file.
// eslint-disable-next-line react-refresh/only-export-components
export function getWeekStart(d) {
  const date = new Date(d)
  date.setHours(0, 0, 0, 0)
  const day = date.getDay() // 0=Sun, 1=Mon…
  const diff = day === 0 ? -6 : 1 - day  // roll back to Monday
  date.setDate(date.getDate() + diff)
  return date
}

export default function CalendarNav({
  year, month, onChange,
  view = 'month', onViewChange,
  weekStart, onWeekChange,
}) {
  function prevMonth() {
    if (month === 0) onChange(year - 1, 11)
    else onChange(year, month - 1)
  }

  function nextMonth() {
    if (month === 11) onChange(year + 1, 0)
    else onChange(year, month + 1)
  }

  function prevWeek() {
    const d = new Date(weekStart)
    d.setDate(d.getDate() - 7)
    onWeekChange?.(d)
  }

  function nextWeek() {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + 7)
    onWeekChange?.(d)
  }

  function goToday() {
    const now = new Date()
    onChange(now.getFullYear(), now.getMonth())
    onWeekChange?.(getWeekStart(now))
  }

  const isWeek = view === 'week'

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6">
      {/* View toggle */}
      <div className="flex gap-0.5 bg-brand-100/70 dark:bg-brand-900/40 rounded-lg p-0.5 self-start sm:self-auto">
        <button
          onClick={() => onViewChange?.('month')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
            !isWeek
              ? 'bg-white dark:bg-brand-800 text-brand-900 dark:text-brand-100 shadow-sm'
              : 'text-brand-500 hover:text-brand-700 dark:hover:text-brand-300'
          }`}
        >
          <FiGrid size={12} /> Month
        </button>
        <button
          onClick={() => onViewChange?.('week')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
            isWeek
              ? 'bg-white dark:bg-brand-800 text-brand-900 dark:text-brand-100 shadow-sm'
              : 'text-brand-500 hover:text-brand-700 dark:hover:text-brand-300'
          }`}
        >
          <FiCalendar size={12} /> Week
        </button>
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-3">
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={isWeek ? prevWeek : prevMonth}
          className="p-2 rounded-xl border border-brand-200/60 dark:border-brand-700/40 text-brand-600 dark:text-brand-400 hover:bg-brand-100/60 dark:hover:bg-brand-800/30 transition-colors"
          title={isWeek ? 'Previous week' : 'Previous month'}
        >
          <FiChevronLeft size={18} />
        </motion.button>

        <h2 className="font-display text-xl sm:text-2xl font-bold text-brand-900 dark:text-brand-100 min-w-[180px] sm:min-w-[200px] text-center tracking-tight">
          {isWeek && weekStart
            ? formatWeekLabel(weekStart)
            : `${MONTH_NAMES[month]} ${year}`}
        </h2>

        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={isWeek ? nextWeek : nextMonth}
          className="p-2 rounded-xl border border-brand-200/60 dark:border-brand-700/40 text-brand-600 dark:text-brand-400 hover:bg-brand-100/60 dark:hover:bg-brand-800/30 transition-colors"
          title={isWeek ? 'Next week' : 'Next month'}
        >
          <FiChevronRight size={18} />
        </motion.button>
      </div>

      <button onClick={goToday} className="btn-secondary text-sm px-3.5 py-1.5 rounded-xl self-start sm:self-auto">
        Today
      </button>
    </div>
  )
}
