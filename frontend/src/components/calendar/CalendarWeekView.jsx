import { motion } from 'framer-motion'
import { resolveUrl } from '../../utils/resolveUrl.js'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function toDateStr(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const OCC_COLORS = {
  casual:  'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  formal:  'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
}


export default function CalendarWeekView({ weekStart, plans, onDayClick }) {
  const today = toDateStr(new Date())

  // Build a map dateStr → plan
  const planMap = {}
  for (const p of plans) {
    planMap[p.plan_date] = p
  }

  // Generate 7 day objects starting from weekStart (Monday)
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + i)
    return { date: d, dateStr: toDateStr(d), label: DAYS[i] }
  })

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="grid grid-cols-7 gap-2"
    >
      {days.map(({ date: d, dateStr, label }) => {
        const plan = planMap[dateStr]
        const isToday = dateStr === today
        const thumbs = plan?.items?.slice(0, 4) ?? []

        return (
          <button
            key={dateStr}
            onClick={() => onDayClick(dateStr, plan || null)}
            className={`flex flex-col rounded-2xl border transition-all group text-left overflow-hidden ${
              isToday
                ? 'border-accent-400 ring-2 ring-accent-400/30 bg-accent-50/40 dark:bg-accent-900/10'
                : 'border-brand-200/60 dark:border-brand-700/40 bg-white dark:bg-brand-900 hover:border-brand-400 dark:hover:border-brand-500'
            }`}
          >
            {/* Day header */}
            <div className={`px-2 py-1.5 flex items-baseline justify-between ${
              isToday ? 'bg-accent-500 text-white' : 'bg-brand-50/60 dark:bg-brand-800/30'
            }`}>
              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                isToday ? 'text-white/80' : 'text-brand-500 dark:text-brand-400'
              }`}>{label}</span>
              <span className={`text-sm font-bold ${
                isToday ? 'text-white' : 'text-brand-700 dark:text-brand-200'
              }`}>{d.getDate()}</span>
            </div>

            {/* Content */}
            <div className="flex-1 p-1.5 space-y-1.5">
              {plan ? (
                <>
                  {/* Image mosaic */}
                  {thumbs.length > 0 ? (
                    <div className={`aspect-square rounded-xl overflow-hidden grid gap-[2px] ${
                      thumbs.length === 1 ? 'grid-cols-1' :
                      thumbs.length === 2 ? 'grid-cols-2' :
                      'grid-cols-2'
                    }`}>
                      {thumbs.map((item, i) => (
                        <div
                          key={i}
                          className={`relative bg-brand-100 dark:bg-brand-800 overflow-hidden ${
                            thumbs.length === 3 && i === 0 ? 'row-span-2' : ''
                          }`}
                        >
                          {item.image_url ? (
                            <img
                              src={resolveUrl(item.image_url)}
                              alt=""
                              className="w-full h-full object-cover"
                              loading="lazy"
                              onError={e => { e.currentTarget.style.display = 'none' }}
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-lg opacity-20">?</div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="aspect-square rounded-xl bg-gradient-to-br from-brand-100 to-brand-200 dark:from-brand-800 dark:to-brand-700 flex items-center justify-center text-2xl opacity-60">
                      {plan.occasion === 'formal' ? '👔' : '👕'}
                    </div>
                  )}

                  {/* Occasion badge */}
                  {plan.occasion && (
                    <span className={`block text-center text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${
                      OCC_COLORS[plan.occasion] ?? 'bg-brand-100 text-brand-600 dark:bg-brand-800 dark:text-brand-300'
                    }`}>
                      {plan.occasion}
                    </span>
                  )}

                  {/* Notes snippet */}
                  {plan.notes && (
                    <p className="text-[10px] text-brand-500 dark:text-brand-400 truncate leading-tight px-0.5">
                      {plan.notes}
                    </p>
                  )}
                </>
              ) : (
                /* Empty day */
                <div className="aspect-square rounded-xl border-2 border-dashed border-brand-200/60 dark:border-brand-700/30 flex items-center justify-center">
                  <span className="text-brand-300 dark:text-brand-600 text-lg group-hover:text-accent-700 transition-colors">+</span>
                </div>
              )}
            </div>
          </button>
        )
      })}
    </motion.div>
  )
}
