import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiCamera, FiPlus } from 'react-icons/fi'
import { getItems, deleteItem } from '../api/wardrobe.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import WardrobeGrid from '../components/wardrobe/WardrobeGrid.jsx'
import UploadModal from '../components/wardrobe/UploadModal.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'

const CATEGORIES = ['all', 'top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']

export default function WardrobePage() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [filter, setFilter] = useState('all')
  const queryClient = useQueryClient()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['wardrobe'],
    queryFn: getItems,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wardrobe'] }),
  })

  const items = data?.items ?? []
  const filtered = filter === 'all' ? items : items.filter(i => i.category === filter)

  return (
    <>
      <PageWrapper>
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="label-xs mb-1">Wardrobe</p>
            <h1 className="font-display text-4xl sm:text-5xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
              My Wardrobe
            </h1>
            <p className="text-brand-500 dark:text-brand-400 mt-1">
              {isLoading ? 'Loading...' : `${items.length} item${items.length !== 1 ? 's' : ''} in your collection`}
            </p>
          </div>
          <button onClick={() => setUploadOpen(true)} className="btn-primary flex items-center gap-2 group">
            <FiPlus size={16} />
            <span className="hidden sm:inline">Upload</span>
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 flex-wrap mb-8">
          {CATEGORIES.map(cat => {
            const count = cat === 'all' ? items.length : items.filter(i => i.category === cat).length
            return (
              <motion.button
                key={cat}
                whileTap={{ scale: 0.96 }}
                onClick={() => setFilter(cat)}
                className={`relative flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  filter === cat
                    ? 'text-brand-900 dark:text-brand-100'
                    : 'text-brand-500 hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-200'
                }`}
              >
                {filter === cat && (
                  <motion.div
                    layoutId="filter-pill"
                    className="absolute inset-0 bg-brand-900/[0.06] dark:bg-brand-100/[0.08] rounded-xl -z-10 border border-brand-200/40 dark:border-brand-700/40"
                    transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }}
                  />
                )}
                <span className="capitalize">{cat}</span>
                <span className={`text-xs font-mono ${filter === cat ? 'text-brand-500 dark:text-brand-400' : 'text-brand-400 dark:text-brand-500'}`}>
                  {count}
                </span>
              </motion.button>
            )
          })}
        </div>

        {/* Content */}
        {isLoading && <LoadingSpinner className="py-16" size="lg" />}
        {error && <ErrorMessage message="Could not load wardrobe." onRetry={refetch} />}
        {!isLoading && !error && (
          <WardrobeGrid
            items={filtered}
            onDelete={id => deleteMutation.mutate(id)}
            onUpload={() => setUploadOpen(true)}
          />
        )}
      </PageWrapper>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  )
}
