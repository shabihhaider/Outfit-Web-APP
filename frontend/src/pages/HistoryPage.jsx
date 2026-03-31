import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiThermometer, FiStar, FiRepeat } from 'react-icons/fi'
import { getHistory } from '../api/outfits.js'
import { saveOutfit } from '../api/outfits.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import OutfitItems from '../components/recommendations/OutfitItems.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import ShareButton from '../components/ui/ShareButton.jsx'
import WearAgainModal from '../components/ui/WearAgainModal.jsx'
import { formatDate, scoreToPercent } from '../utils/formatters.js'

export default function HistoryPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [wearAgainTarget, setWearAgainTarget] = useState(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['history'],
    queryFn: getHistory,
  })

  const saveMutation = useMutation({
    mutationFn: (outfit) => {
      const items = outfit.items?.map(i => i.id) ?? []
      return saveOutfit({
        name: `${outfit.occasion} wear-again ${Date.now()}`,
        occasion: outfit.occasion,
        item_ids: items,
        final_score: outfit.final_score,
        confidence: outfit.confidence,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved'] })
      setWearAgainTarget(null)
    },
  })

  const history = data?.history ?? []

  return (
    <>
      <PageWrapper>
        <div className="mb-8">
          <p className="label-xs mb-1">History</p>
          <h1 className="font-display text-4xl sm:text-5xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
            Recommendation History
          </h1>
          <p className="text-brand-500 dark:text-brand-400 mt-1">Your past outfit recommendations</p>
        </div>

        {isLoading && <LoadingSpinner className="py-16" size="lg" />}
        {error && <ErrorMessage message="Could not load history." onRetry={refetch} />}

        {!isLoading && !error && history.length === 0 && (
          <EmptyState
            icon="📋"
            title="No history yet"
            description="Your recommendation history will appear here once you get your first outfit suggestion."
            action={{ label: 'Get Recommendations', icon: FiStar, onClick: () => navigate('/recommendations') }}
          />
        )}

        {!isLoading && history.length > 0 && (
          <div className="space-y-4">
            {history.map((entry, idx) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: idx * 0.04, ease: [0.16, 1, 0.3, 1] }}
                className="card p-5 hover:shadow-card-hover transition-all duration-300"
              >
                <div className="flex items-center gap-3 mb-4 flex-wrap">
                  <span className="badge-casual capitalize">{entry.occasion}</span>
                  <span className="text-sm text-brand-500 dark:text-brand-400 flex items-center gap-1">
                    <FiThermometer size={13} />
                    <span className="font-mono text-xs">{entry.temperature_used}{'\u00B0'}C</span>
                  </span>
                  {entry.final_score != null && (
                    <span className="text-sm text-brand-500 dark:text-brand-400">
                      <span className="data-value text-sm">{scoreToPercent(entry.final_score)}%</span> compatible
                    </span>
                  )}
                  <span className="text-xs text-brand-400 dark:text-brand-500 ml-auto">{formatDate(entry.logged_at ?? entry.created_at)}</span>
                </div>
                <OutfitItems items={entry.items ?? []} />

                <div className="mt-3 pt-3 border-t border-brand-100/60 dark:border-brand-800/40 flex items-center gap-4">
                  <button
                    onClick={() => setWearAgainTarget(entry)}
                    className="inline-flex items-center gap-1.5 text-sm text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 font-medium transition-colors"
                  >
                    <FiRepeat size={14} />
                    Wear Again
                  </button>
                  <ShareButton outfit={entry} items={entry.items ?? []} />
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </PageWrapper>

      <WearAgainModal
        outfit={wearAgainTarget}
        open={!!wearAgainTarget}
        onClose={() => setWearAgainTarget(null)}
        onSave={(outfit) => saveMutation.mutate(outfit)}
        onCalendar={() => { setWearAgainTarget(null); navigate('/calendar') }}
      />
    </>
  )
}
