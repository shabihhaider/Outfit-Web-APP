import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiBarChart2, FiZap, FiInfo, FiTrendingUp, FiArrowRight } from 'react-icons/fi'
import { getWardrobeStats } from '../../api/wardrobe.js'
import { pluralizeCategory, scoreToLabel } from '../../utils/formatters.js'

const CAT_COLORS = {
  top: 'bg-sky-500',
  bottom: 'bg-indigo-500',
  outwear: 'bg-amber-500',
  shoes: 'bg-emerald-500',
  dress: 'bg-pink-500',
  jumpsuit: 'bg-purple-500',
}

function CategoryBar({ category, count, max, delay }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-[11px] text-brand-600 dark:text-brand-400 w-20 text-right capitalize font-medium">{pluralizeCategory(category)}</span>
      <div className="flex-1 h-3 bg-brand-100/60 dark:bg-brand-800/40 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
          className={`h-full rounded-full ${CAT_COLORS[category] || 'bg-brand-400'}`}
        />
      </div>
      <span className="text-[11px] font-mono font-semibold text-brand-700 dark:text-brand-300 w-6 text-right">{count}</span>
    </div>
  )
}

function ColorDot({ hue, sat, val }) {
  const l = val * (1 - sat / 2)
  const s = l === 0 || l === 1 ? 0 : ((val - l) / Math.min(l, 1 - l)) * 100
  const color = `hsl(${hue}, ${Math.round(s)}%, ${Math.round(l * 100)}%)`
  return (
    <motion.div
      whileHover={{ scale: 1.3 }}
      className="w-6 h-6 rounded-full border border-brand-200/60 dark:border-brand-700/40 shadow-sm cursor-default"
      style={{ backgroundColor: color }}
      title={`H:${Math.round(hue)} S:${(sat * 100).toFixed(0)}% V:${(val * 100).toFixed(0)}%`}
    />
  )
}

export default function WardrobeStats() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['wardrobe-stats'],
    queryFn: getWardrobeStats,
    staleTime: 2 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="card p-6">
        <div className="skeleton h-6 w-40 rounded-lg mb-4" />
        <div className="space-y-3">
          {[1,2,3,4].map(i => <div key={i} className="skeleton h-4 w-full rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6">
        <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200 mb-2">Wardrobe Insights</h2>
        <p className="text-sm text-brand-500 dark:text-brand-400">Could not load statistics.</p>
      </div>
    )
  }

  const { wardrobe = {}, activity = {}, insights = {} } = data ?? {}
  const categories = wardrobe.categories ?? {}
  const colors = wardrobe.colors ?? []
  const feedback = activity.feedback ?? {}
  const maxCount = Math.max(...Object.values(categories), 1)
  const capacityPct = Math.round(((wardrobe.total_items ?? 0) / (wardrobe.capacity ?? 50)) * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="card p-6"
    >
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-accent-100/80 dark:bg-accent-900/25 flex items-center justify-center">
          <FiBarChart2 className="text-accent-700" size={16} />
        </div>
        <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200">Insights</h2>
      </div>

      {/* Item count — capability framing */}
      <div className="mb-6">
        <p className="text-xs text-brand-500 dark:text-brand-400 mb-1">
          <span className="font-semibold text-brand-700 dark:text-brand-300">{wardrobe.total_items ?? 0} items</span>
          {(wardrobe.total_items ?? 0) > 0 ? ' — ready for recommendations' : ' — upload your first item to get started'}
        </p>
      </div>

      {/* Categories */}
      <div className="space-y-2.5 mb-6">
        {Object.entries(categories).map(([cat, count], i) => (
          <CategoryBar key={cat} category={cat} count={count} max={maxCount} delay={i * 0.06} />
        ))}
      </div>

      {/* Colors */}
      {colors.length > 0 && (
        <div className="mb-6">
          <p className="label-xs mb-2">Color Palette</p>
          <div className="flex flex-wrap gap-1.5">
            {colors.map((c, i) => (
              <ColorDot key={i} hue={c.hue} sat={c.sat} val={c.val} />
            ))}
          </div>
        </div>
      )}

      {/* Activity */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="bg-brand-50/60 dark:bg-brand-800/30 rounded-xl p-3 text-center border border-brand-100/40 dark:border-brand-800/30">
          <div className="text-xl font-mono font-bold text-brand-900 dark:text-brand-100">{activity.total_recommendations ?? 0}</div>
          <div className="text-[10px] text-brand-500 dark:text-brand-400 mt-0.5">Recommendations</div>
        </div>
        <div className="bg-brand-50/60 dark:bg-brand-800/30 rounded-xl p-3 text-center border border-brand-100/40 dark:border-brand-800/30">
          <div className="text-xl font-mono font-bold text-brand-900 dark:text-brand-100">{activity.saved_outfits ?? 0}</div>
          <div className="text-[10px] text-brand-500 dark:text-brand-400 mt-0.5">Saved</div>
        </div>
        {activity.avg_score != null && (
          <div className="bg-brand-50/60 dark:bg-brand-800/30 rounded-xl p-3 text-center border border-brand-100/40 dark:border-brand-800/30">
            <div className="text-xl font-mono font-bold text-brand-900 dark:text-brand-100">{Math.round(activity.avg_score * 100)}%</div>
            <div className="text-[10px] font-medium text-accent-700 dark:text-accent-400 mt-0.5">{scoreToLabel(activity.avg_score)}</div>
          </div>
        )}
        {(feedback.thumbs_up > 0 || feedback.thumbs_down > 0) && (
          <div className="bg-brand-50/60 dark:bg-brand-800/30 rounded-xl p-3 text-center border border-brand-100/40 dark:border-brand-800/30">
            <div className="text-lg font-mono font-bold">
              <span className="text-emerald-600 dark:text-emerald-400">{feedback.thumbs_up ?? 0}</span>
              <span className="text-brand-300 dark:text-brand-600 mx-0.5">/</span>
              <span className="text-red-500 dark:text-red-400">{feedback.thumbs_down ?? 0}</span>
            </div>
            <div className="text-[10px] text-brand-500 dark:text-brand-400 mt-0.5">Feedback</div>
          </div>
        )}
      </div>

      {/* Insights */}
      {insights.wardrobe_balance && (
        <div className="flex items-start gap-2.5 p-3 bg-accent-50/60 dark:bg-accent-900/10 border border-accent-200/40 dark:border-accent-800/30 rounded-xl text-sm text-accent-700 dark:text-accent-300">
          <FiZap size={14} className="mt-0.5 flex-shrink-0" />
          <span>{insights.wardrobe_balance}</span>
        </div>
      )}

      {(insights.never_used_item_ids?.length ?? 0) > 0 && (
        <div className="p-3 mt-2 bg-sky-50/60 dark:bg-sky-900/10 border border-sky-200/40 dark:border-sky-800/30 rounded-xl">
          <div className="flex items-start gap-2.5 text-sm text-sky-700 dark:text-sky-300 mb-2">
            <FiInfo size={14} className="mt-0.5 flex-shrink-0" />
            <span>
              {insights.never_used_item_ids.length} item{insights.never_used_item_ids.length !== 1 ? 's' : ''} waiting to shine — try a new occasion to unlock them.
            </span>
          </div>
          <a
            href="/recommendations"
            className="flex items-center gap-1 text-[11px] font-medium text-sky-600 dark:text-sky-400 hover:underline ml-6"
          >
            Explore recommendations <FiArrowRight size={11} />
          </a>
        </div>
      )}

      {insights.most_common_occasion && (
        <p className="flex items-center gap-1.5 text-xs text-brand-500 dark:text-brand-400 mt-3">
          <FiTrendingUp size={12} />
          Most requested: <span className="font-medium capitalize text-brand-600 dark:text-brand-300">{insights.most_common_occasion}</span>
        </p>
      )}
    </motion.div>
  )
}
