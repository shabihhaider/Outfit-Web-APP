import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiCamera, FiStar, FiBookmark, FiAlertTriangle, FiCheckCircle, FiGrid, FiArrowRight, FiCalendar } from 'react-icons/fi'
import { getItems } from '../api/wardrobe.js'
import { getHistory } from '../api/outfits.js'
import { getTodayPlan } from '../api/notifications.js'
import { useAuth } from '../context/AuthContext.jsx'
import { getGreeting, formatDate, scoreToPercent, pluralizeCategory } from '../utils/formatters.js'
import { getWardrobeHealth } from '../utils/wardrobeHealth.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import RetryImage from '../components/ui/RetryImage.jsx'
import OOTDWidget from '../components/dashboard/OOTDWidget.jsx'
import WardrobeStats from '../components/dashboard/WardrobeStats.jsx'
import StyleDNACard from '../components/social/StyleDNACard.jsx'
import { resolveUrl } from '../utils/resolveUrl.js'
// import EidPlannerWidget from '../components/social/EidPlannerWidget.jsx'

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } }
const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } } }

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const { data: wardrobeData, isLoading: wLoading } = useQuery({
    queryKey: ['wardrobe'],
    queryFn: getItems,
  })

  const { data: historyData } = useQuery({
    queryKey: ['history'],
    queryFn: getHistory,
  })

  const { data: todayData } = useQuery({
    queryKey: ['today-plan'],
    queryFn: getTodayPlan,
    staleTime: 5 * 60 * 1000,
  })
  const todayPlan = todayData?.plan ?? null

  const items = wardrobeData?.items ?? []
  const health = getWardrobeHealth(items)
  const recentHistory = historyData?.history?.slice(0, 3) ?? []

  return (
    <PageWrapper>
      <motion.div variants={stagger} initial="hidden" animate="show">
        {/* Greeting */}
        <motion.div variants={fadeUp} className="mb-10">
          <p className="label-xs mb-2">Dashboard</p>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold text-brand-900 dark:text-brand-100 leading-[1.1] tracking-tight">
            {getGreeting()},<br />
            <span className="text-accent-700 italic">{user?.name || 'there'}</span>
          </h1>
        </motion.div>

        {/* OOTD Widget */}
        <motion.div variants={fadeUp} className="mb-8">
          <OOTDWidget />
        </motion.div>

        {/* Today's Look banner */}
        {todayPlan && (
          <motion.div
            variants={fadeUp}
            className="mb-8 flex items-center gap-4 p-4 rounded-2xl bg-gradient-to-r from-accent-50 to-violet-50 dark:from-accent-900/20 dark:to-violet-900/15 border border-accent-200/60 dark:border-accent-700/30"
          >
            {/* Thumbnails */}
            <div className="flex -space-x-2 flex-shrink-0">
              {(todayPlan.items ?? []).slice(0, 3).map((item, i) => (
                <div
                  key={i}
                  className="w-10 h-10 rounded-full overflow-hidden border-2 border-white dark:border-brand-900 bg-brand-100 dark:bg-brand-800"
                >
                  <RetryImage
                    src={resolveUrl(item.image_url)}
                    alt={item.category}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-full object-cover"
                    fallback={
                      <div className="w-full h-full flex items-center justify-center text-lg opacity-30">
                        {todayPlan.occasion === 'formal' ? '👔' : '👕'}
                      </div>
                    }
                  />
                </div>
              ))}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-accent-700 dark:text-accent-400 uppercase tracking-wider mb-0.5">
                Today&apos;s Planned Look
              </p>
              <p className="text-sm font-medium text-brand-700 dark:text-brand-200 capitalize truncate">
                {todayPlan.occasion ?? 'Outfit'} ensemble
                {todayPlan.notes ? ` · ${todayPlan.notes}` : ''}
              </p>
            </div>
            <button
              onClick={() => navigate('/calendar')}
              className="flex-shrink-0 flex items-center gap-1.5 text-xs font-semibold text-accent-700 dark:text-accent-400 hover:underline"
            >
              <FiCalendar size={13} /> View Calendar
            </button>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Wardrobe Health */}
          <motion.div variants={fadeUp} className="lg:col-span-2 card p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200">Wardrobe Health</h2>
              <button
                onClick={() => navigate('/wardrobe')}
                className="text-sm text-brand-500 hover:text-accent-700 dark:hover:text-accent-700 transition-colors flex items-center gap-1"
              >
                View all <FiArrowRight size={14} />
              </button>
            </div>

            {wLoading ? (
              <LoadingSpinner className="py-8" label="Loading your wardrobe..." />
            ) : (
              <>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-5">
                  {Object.entries(health.counts).map(([cat, count], i) => (
                    <motion.div
                      key={cat}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.05, duration: 0.3 }}
                      className="text-center p-3 bg-brand-50/80 dark:bg-brand-800/40 rounded-xl border border-brand-100/60 dark:border-brand-800/40"
                    >
                      <div className="text-3xl font-mono font-bold text-brand-900 dark:text-brand-100">{count}</div>
                      <div className="label-xs mt-1">{pluralizeCategory(cat)}</div>
                    </motion.div>
                  ))}
                </div>

                {health.gaps.length > 0 && (
                  <div className="space-y-2">
                    {health.gaps.map((gap, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-3 bg-amber-50/80 dark:bg-amber-900/15 border border-amber-200/60 dark:border-amber-800/40 rounded-xl text-sm text-amber-700 dark:text-amber-300">
                        <FiAlertTriangle size={15} className="mt-0.5 flex-shrink-0" /> {gap}
                      </div>
                    ))}
                  </div>
                )}

                {health.gaps.length === 0 && items.length > 0 && (
                  <div className="flex items-center gap-2.5 p-3 bg-emerald-50/80 dark:bg-emerald-900/15 border border-emerald-200/60 dark:border-emerald-800/40 rounded-xl text-sm text-emerald-700 dark:text-emerald-300">
                    <FiCheckCircle size={15} /> Your wardrobe is ready for recommendations!
                  </div>
                )}

                {items.length === 0 && (
                  <div className="flex items-center gap-2.5 p-3 bg-brand-50/80 dark:bg-brand-800/30 border border-brand-200/60 dark:border-brand-700/40 rounded-xl text-sm text-brand-500 dark:text-brand-400">
                    <FiGrid size={15} /> Upload your first item to get started.
                  </div>
                )}
              </>
            )}
          </motion.div>

          {/* Quick Actions */}
          <motion.div variants={fadeUp} className="card p-6">
            <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200 mb-5">Quick Actions</h2>
            <div className="space-y-3">
              <button onClick={() => navigate('/wardrobe')} className="w-full btn-primary flex items-center gap-2.5 justify-center group">
                <FiCamera size={16} /> Upload Item <FiArrowRight size={14} className="opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-0.5" />
              </button>
              <button onClick={() => navigate('/recommendations')} className="w-full btn-secondary flex items-center gap-2.5 justify-center">
                <FiStar size={16} /> Get Recommendations
              </button>
              <button onClick={() => navigate('/outfits/saved')} className="w-full btn-secondary flex items-center gap-2.5 justify-center">
                <FiBookmark size={16} /> Saved Outfits
              </button>
            </div>

            <div className="mt-6 pt-6 border-t border-brand-100/80 dark:border-brand-800/60 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-brand-500 dark:text-brand-400">Total items</span>
                <span className="data-value">{health.total}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-brand-500 dark:text-brand-400">Recommendations</span>
                <span className="data-value">{historyData?.count ?? 0}</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Recent history + Stats */}
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
          <motion.div variants={fadeUp} className="lg:col-span-2">
            {recentHistory.length > 0 && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200">Recent</h2>
                  <button
                    onClick={() => navigate('/outfits/history')}
                    className="text-sm text-brand-500 hover:text-accent-700 dark:hover:text-accent-700 transition-colors flex items-center gap-1"
                  >
                    View all <FiArrowRight size={14} />
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {recentHistory.map((entry, idx) => (
                    <motion.div
                      key={entry.id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, delay: idx * 0.08 }}
                      className="card-hover p-4"
                      onClick={() => navigate('/outfits/history')}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="badge-casual capitalize">{entry.occasion}</span>
                        <span className="text-xs text-brand-500 dark:text-brand-400">{formatDate(entry.created_at)}</span>
                      </div>
                      <div className="flex gap-1 flex-wrap">
                        {entry.items?.slice(0, 3).map((item, i) => (
                          <span key={i} className={`badge-${item.category}`}>{item.category}</span>
                        ))}
                      </div>
                      {entry.final_score != null && (
                        <div className="mt-3 text-sm text-brand-500 dark:text-brand-400">
                          <span className="data-value text-sm">{scoreToPercent(entry.final_score)}%</span>
                          <span className="ml-1">compatible</span>
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </>
            )}
          </motion.div>

          <motion.div variants={fadeUp} className="lg:col-span-1 space-y-6">
            <WardrobeStats />
            <StyleDNACard />
          </motion.div>
        </div>
      </motion.div>
    </PageWrapper>
  )
}
