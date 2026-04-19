import { motion } from 'framer-motion'
import { FiBriefcase, FiSun } from 'react-icons/fi'
import { resolveUrl } from '../../utils/resolveUrl.js'
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const OCCASION_ICON = {
  casual: FiSun,
  formal: FiBriefcase,
}

export default function CalendarGrid({ year, month, plans, onDayClick }) {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  const planMap = {}
  for (const plan of plans) {
    planMap[plan.plan_date] = plan
  }

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()

  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6

  const totalCells = Math.ceil((startDow + daysInMonth) / 7) * 7
  const cells = []

  for (let i = 0; i < totalCells; i++) {
    const dayNum = i - startDow + 1
    if (dayNum < 1 || dayNum > daysInMonth) {
      cells.push({ dayNum: null, dateStr: null })
    } else {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`
      cells.push({ dayNum, dateStr })
    }
  }

  return (
    <div>
      <div className="grid grid-cols-7 gap-1 mb-1">
        {DAY_NAMES.map(d => (
          <div key={d} className="text-center text-[9px] sm:text-[11px] font-semibold text-brand-500 dark:text-brand-400 py-2 uppercase tracking-wider">{d}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-0.5 sm:gap-1">
        {cells.map((cell, i) => {
          if (cell.dayNum === null) {
            return <div key={i} className="h-14 sm:h-24 rounded-lg sm:rounded-xl" />
          }

          const plan = planMap[cell.dateStr]
          const isToday = cell.dateStr === todayStr
          const isPast = cell.dateStr < todayStr
          const OccIcon = plan?.occasion ? OCCASION_ICON[plan.occasion] : null

          return (
            <motion.button
              key={i}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2, delay: i * 0.008 }}
              onClick={() => onDayClick(cell.dateStr, plan)}
              className={`h-14 sm:h-24 rounded-lg sm:rounded-xl border text-left p-1 sm:p-2 transition-all hover:shadow-card-hover
                ${isToday
                  ? 'border-accent-400/60 bg-accent-50/60 dark:bg-accent-900/10 dark:border-accent-600/30 ring-1 ring-accent-200/60 dark:ring-accent-700/30'
                  : plan
                    ? 'border-emerald-200/60 bg-emerald-50/60 dark:bg-emerald-900/10 dark:border-emerald-700/30'
                    : 'border-brand-100/60 dark:border-brand-800/40 bg-white/60 dark:bg-brand-900/30 hover:bg-brand-50/80 dark:hover:bg-brand-800/30'
                }
                ${isPast && !isToday ? 'opacity-50' : ''}
              `}
            >
              <div className="flex items-center justify-between">
                {isToday ? (
                  <span className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-accent-500 flex items-center justify-center text-[10px] sm:text-xs font-bold text-white flex-shrink-0">
                    {cell.dayNum}
                  </span>
                ) : (
                  <span className="text-xs sm:text-sm font-medium text-brand-700 dark:text-brand-300">
                    {cell.dayNum}
                  </span>
                )}
                {OccIcon && <OccIcon size={9} className="hidden sm:block text-brand-500 dark:text-brand-400" />}
              </div>

              {plan && (
                <div className="mt-0.5 sm:mt-1">
                  <div className="flex gap-0.5">
                    {plan.items?.slice(0, 2).map((item, j) => (
                      <div key={j} className="w-4 h-4 sm:w-5 sm:h-5 rounded overflow-hidden bg-brand-100 dark:bg-brand-800 flex-shrink-0">
                        {item.image_url && (
                          <img src={resolveUrl(item.image_url)} alt="" className="w-full h-full object-cover" />
                        )}
                      </div>
                    ))}
                    {plan.items?.length > 2 && (
                      <span className="text-[9px] text-brand-500 dark:text-brand-400">+{plan.items.length - 2}</span>
                    )}
                  </div>
                  {plan.notes && (
                    <p className="hidden sm:block text-[10px] text-brand-500 dark:text-brand-400 truncate mt-0.5">{plan.notes}</p>
                  )}
                </div>
              )}

              {!plan && isToday && (
                <span className="hidden sm:inline-block mt-1 text-[9px] font-semibold px-1.5 py-0.5 rounded border border-accent-400/60 text-accent-700 dark:text-accent-400 dark:border-accent-600/50">
                  Plan today
                </span>
              )}
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
