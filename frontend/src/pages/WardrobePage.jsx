import { useState, useRef, useCallback, useMemo } from 'react'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiPlus, FiCheckSquare, FiX, FiTrash2, FiLoader, FiSearch, FiSliders } from 'react-icons/fi'
import { getItems, deleteItem, bulkDeleteItems, bulkUpdateFormality } from '../api/wardrobe.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import WardrobeGrid from '../components/wardrobe/WardrobeGrid.jsx'
import UploadModal from '../components/wardrobe/UploadModal.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'

const CATEGORIES = ['all', 'top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']
const FORMALITIES = ['casual', 'formal', 'both']
const SORT_OPTIONS = [
  { key: 'newest',          label: 'Newest First' },
  { key: 'oldest',          label: 'Oldest First' },
  { key: 'confidence_desc', label: 'Highest Confidence' },
  { key: 'confidence_asc',  label: 'Lowest Confidence' },
]

function sortItems(items, key) {
  const arr = [...items]
  switch (key) {
    case 'oldest':
      return arr.sort((a, b) => (a.id ?? 0) - (b.id ?? 0))
    case 'confidence_desc':
      return arr.sort((a, b) => (b.model_confidence ?? 0) - (a.model_confidence ?? 0))
    case 'confidence_asc':
      return arr.sort((a, b) => (a.model_confidence ?? 0) - (b.model_confidence ?? 0))
    case 'newest':
    default:
      return arr.sort((a, b) => (b.id ?? 0) - (a.id ?? 0))
  }
}

export default function WardrobePage() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [filter, setFilter] = useState('all')
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [formalityFilter, setFormalityFilter] = useState('all')
  const [sortKey, setSortKey] = useState('newest')
  const queryClient = useQueryClient()

  const {
    data,
    isLoading,
    error,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['wardrobe', filter],
    queryFn: ({ pageParam = 1 }) => getItems({ page: pageParam, limit: 20, category: filter }),
    getNextPageParam: (lastPage) => lastPage.has_next ? lastPage.page + 1 : undefined,
    staleTime: 60 * 1000,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wardrobe'] }),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids) => bulkDeleteItems([...ids]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] })
      exitSelectMode()
    },
  })

  const bulkFormalityMutation = useMutation({
    mutationFn: ({ ids, formality }) => bulkUpdateFormality([...ids], formality),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] })
      exitSelectMode()
    },
  })

  // Flatten all loaded pages
  const items = data?.pages.flatMap(p => p.items) ?? []
  const totalItems = data?.pages[0]?.total ?? 0

  const filteredItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return sortItems(
      items
        .filter(item => formalityFilter === 'all' || item.formality === formalityFilter)
        .filter(item => !q || (item.sub_category ?? item.category ?? '').toLowerCase().includes(q)),
      sortKey
    )
  }, [items, searchQuery, formalityFilter, sortKey])

  const hasActiveFilters = searchQuery.trim() !== '' || formalityFilter !== 'all' || sortKey !== 'newest'

  function clearFilters() {
    setSearchQuery('')
    setFormalityFilter('all')
    setSortKey('newest')
  }

  function handleFilterChange(cat) {
    setFilter(cat)
    exitSelectMode()
  }

  function toggleSelect(id) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function exitSelectMode() {
    setSelectMode(false)
    setSelectedIds(new Set())
  }

  function selectAll() {
    setSelectedIds(new Set(filteredItems.map(i => i.id)))
  }

  const selCount = selectedIds.size

  // Category counts from loaded items (updates as more pages load)
  function catCount(cat) {
    if (cat === 'all') return totalItems
    if (filter === cat) return totalItems
    if (filter !== 'all') return 0
    return items.filter(i => i.category === cat).length
  }

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
              {isLoading
                ? 'Loading your wardrobe items...'
                : hasActiveFilters
                ? `${filteredItems.length} of ${items.length} items`
                : `${totalItems || items.length} item${(totalItems || items.length) !== 1 ? 's' : ''} in your collection`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {selectMode ? (
              <>
                <button
                  onClick={selCount === filteredItems.length ? () => setSelectedIds(new Set()) : selectAll}
                  className="h-9 px-3 rounded-xl text-xs font-medium text-brand-500 dark:text-brand-400 border border-brand-200/60 dark:border-brand-700/40 hover:bg-brand-50 dark:hover:bg-brand-800/40 transition-all"
                >
                  {selCount === filteredItems.length ? 'Deselect All' : 'Select All'}
                </button>
                <button onClick={exitSelectMode} className="h-9 px-3 rounded-xl text-xs font-medium btn-secondary flex items-center gap-1.5">
                  <FiX size={13} /> Done
                </button>
              </>
            ) : (
              <>
                {totalItems > 0 && (
                  <button
                    onClick={() => setSelectMode(true)}
                    className="h-9 px-3 rounded-xl text-xs font-medium text-brand-500 dark:text-brand-400 border border-brand-200/60 dark:border-brand-700/40 hover:bg-brand-50 dark:hover:bg-brand-800/40 transition-all flex items-center gap-1.5"
                  >
                    <FiCheckSquare size={13} /> Select
                  </button>
                )}
                <button onClick={() => setUploadOpen(true)} className="btn-primary flex items-center gap-2 group">
                  <FiPlus size={16} />
                  <span className="hidden sm:inline">Upload</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Category tabs */}
        <div className="flex gap-2 flex-wrap mb-4">
          {CATEGORIES.map(cat => {
            const count = catCount(cat)
            return (
              <motion.button
                key={cat}
                whileTap={{ scale: 0.96 }}
                onClick={() => handleFilterChange(cat)}
                style={{ touchAction: 'manipulation' }}
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
                <span className="text-xs font-mono text-brand-500 dark:text-brand-400">{count}</span>
              </motion.button>
            )
          })}
        </div>

        {/* Search + sort + formality controls */}
        {!isLoading && items.length > 0 && (
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            {/* Search */}
            <div className="relative flex-1">
              <FiSearch size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search by type (e.g. kurta, polo)…"
                className="w-full pl-8 pr-8 py-2 rounded-xl border border-brand-200/60 dark:border-brand-700/40 bg-white dark:bg-brand-900 text-sm text-brand-800 dark:text-brand-200 placeholder:text-brand-400 dark:placeholder:text-brand-500 focus:outline-none focus:ring-2 focus:ring-accent-400/40 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-400 hover:text-brand-600 transition-colors"
                >
                  <FiX size={13} />
                </button>
              )}
            </div>

            {/* Sort */}
            <div className="relative">
              <FiSliders size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400 pointer-events-none" />
              <select
                value={sortKey}
                onChange={e => setSortKey(e.target.value)}
                className="pl-8 pr-8 py-2 rounded-xl border border-brand-200/60 dark:border-brand-700/40 bg-white dark:bg-brand-900 text-sm text-brand-700 dark:text-brand-200 focus:outline-none focus:ring-2 focus:ring-accent-400/40 transition-all appearance-none cursor-pointer"
              >
                {SORT_OPTIONS.map(opt => (
                  <option key={opt.key} value={opt.key}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Formality filter chips */}
        {!isLoading && items.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap mb-6">
            <span className="text-xs text-brand-500 dark:text-brand-400 font-medium">Formality:</span>
            {['all', ...FORMALITIES].map(f => (
              <button
                key={f}
                onClick={() => setFormalityFilter(f)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium border transition-all ${
                  formalityFilter === f
                    ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100'
                    : 'border-brand-200/60 dark:border-brand-700/40 text-brand-500 dark:text-brand-400 hover:border-brand-400 dark:hover:border-brand-500'
                }`}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-xs px-3 py-1.5 rounded-full font-medium border border-dashed border-brand-300 dark:border-brand-600 text-brand-500 dark:text-brand-400 hover:border-red-400 hover:text-red-500 transition-all flex items-center gap-1"
              >
                <FiX size={11} /> Clear filters
              </button>
            )}
          </div>
        )}

        {/* Content */}
        {isLoading && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="card overflow-hidden">
                <div className="skeleton aspect-square" />
                <div className="p-3 space-y-2">
                  <div className="skeleton h-4 w-16 rounded" />
                  <div className="skeleton h-3 w-24 rounded" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <ErrorMessage message="Could not load wardrobe." onRetry={refetch} />}
        {!isLoading && !error && (
          <WardrobeGrid
            items={filteredItems}
            onDelete={id => deleteMutation.mutate(id)}
            onUpload={() => setUploadOpen(true)}
            selectMode={selectMode}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            filter={filter}
          />
        )}

        {/* Load more */}
        {hasNextPage && !isLoading && (
          <div className="flex justify-center mt-8">
            <button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="btn-secondary flex items-center gap-2 disabled:opacity-60"
            >
              {isFetchingNextPage
                ? <><FiLoader size={14} className="animate-spin" /> Loading…</>
                : `Load more (${totalItems - items.length} remaining)`}
            </button>
          </div>
        )}
      </PageWrapper>

      {/* Bulk action bar */}
      <AnimatePresence>
        {selectMode && selCount > 0 && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 bg-brand-900 dark:bg-brand-100 text-white dark:text-brand-900 rounded-2xl shadow-2xl px-5 py-3"
          >
            <span className="text-sm font-semibold mr-1">{selCount} selected</span>

            {/* Bulk formality */}
            <div className="flex gap-1.5 border-l border-white/20 dark:border-brand-900/20 pl-3">
              {FORMALITIES.map(f => (
                <button
                  key={f}
                  onClick={() => bulkFormalityMutation.mutate({ ids: selectedIds, formality: f })}
                  disabled={bulkFormalityMutation.isPending}
                  className="h-8 px-3 rounded-lg text-xs font-medium bg-white/15 dark:bg-brand-900/15 hover:bg-white/25 dark:hover:bg-brand-900/25 capitalize transition-all disabled:opacity-50"
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Bulk delete */}
            <button
              onClick={() => setConfirmBulkDelete(true)}
              className="h-8 w-8 rounded-lg flex items-center justify-center bg-red-500/80 hover:bg-red-500 transition-all ml-1"
              title="Delete selected"
            >
              <FiTrash2 size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />

      <ConfirmDialog
        open={confirmBulkDelete}
        title={`Delete ${selCount} item${selCount !== 1 ? 's' : ''}?`}
        message={`Remove ${selCount} item${selCount !== 1 ? 's' : ''} from your wardrobe? This cannot be undone.`}
        danger
        onConfirm={() => { setConfirmBulkDelete(false); bulkDeleteMutation.mutate(selectedIds) }}
        onCancel={() => setConfirmBulkDelete(false)}
      />
    </>
  )
}
