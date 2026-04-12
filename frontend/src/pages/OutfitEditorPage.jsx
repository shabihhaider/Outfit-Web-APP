import { useState, useMemo, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiPlus, FiCalendar, FiBookmark, FiAlertTriangle, FiZap, FiDroplet, FiThermometer, FiCpu, FiCheck, FiLayers, FiMaximize2, FiMinimize2, FiTrash2, FiChevronDown, FiUser } from 'react-icons/fi'
import { toast } from 'sonner'
import { getItems } from '../api/wardrobe.js'
import { scoreOutfit } from '../api/recommendations.js'
import { saveOutfit } from '../api/outfits.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import ConfidenceBadge from '../components/ui/ConfidenceBadge.jsx'
import CustomSelect from '../components/ui/CustomSelect.jsx'
import { scoreToPercent } from '../utils/formatters.js'
import OutfitTryOnModal from '../components/tryon/OutfitTryOnModal.jsx'
import { resolveUrl } from '../utils/resolveUrl.js'

const CAT_EMOJI = { top: '👕', bottom: '👖', outwear: '🧥', shoes: '👟', dress: '👗', jumpsuit: '🧘' }
const CATEGORIES = ['all', 'top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']
const OCCASIONS = [
  { value: 'casual', label: 'Casual' },
  { value: 'formal', label: 'Formal' },
  { value: 'wedding', label: 'Wedding' }
]

export default function OutfitEditorPage() {
  const [canvasItems, setCanvasItems] = useState([])
  const [occasion, setOccasion] = useState('casual')
  const [tempCelsius, setTempCelsius] = useState(25)
  const [sidebarFilter, setSidebarFilter] = useState('all')
  const [saved, setSaved] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [scoreModalOpen, setScoreModalOpen] = useState(false)
  const [canvasFullscreen, setCanvasFullscreen] = useState(false)
  const [tryOnOpen, setTryOnOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  const { data: wardrobeData, isLoading, error } = useQuery({
    queryKey: ['wardrobe'],
    queryFn: getItems,
  })

  const items = wardrobeData?.items ?? []
  const canvasItemIds = useMemo(() => new Set(canvasItems.map(i => i.id)), [canvasItems])

  // Pre-load canvas when navigated from a Remix action
  const remixItemIds = location.state?.remixItemIds
  useEffect(() => {
    if (!remixItemIds?.length || !items.length || canvasItems.length > 0) return
    const preload = remixItemIds
      .map(id => items.find(i => i.id === id))
      .filter(Boolean)
    if (preload.length > 0) setCanvasItems(preload)
  }, [remixItemIds, items]) // eslint-disable-line react-hooks/exhaustive-deps

  const sidebarItems = useMemo(() => {
    const available = items.filter(i => !canvasItemIds.has(i.id))
    if (sidebarFilter === 'all') return available
    return available.filter(i => i.category === sidebarFilter)
  }, [items, canvasItemIds, sidebarFilter])

  const itemIds = useMemo(() => canvasItems.map(i => i.id), [canvasItems])

  const scoreQuery = useQuery({
    queryKey: ['score-outfit', itemIds, occasion, tempCelsius],
    queryFn: () => scoreOutfit({ item_ids: itemIds, occasion, temp_celsius: tempCelsius }),
    enabled: itemIds.length >= 2,
    keepPreviousData: true,
    staleTime: 30000,
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const cats = canvasItems.map(i => i.category).map(c => c.charAt(0).toUpperCase() + c.slice(1)).join(' + ')
      const now = new Date()
      const dateStr = now.toLocaleString('en', { month: 'short', day: 'numeric' })
      return saveOutfit({
        name: `${occasion.charAt(0).toUpperCase() + occasion.slice(1)} ${cats} · ${dateStr}`,
        occasion,
        item_ids: itemIds,
        final_score: scoreQuery.data?.final_score ?? 0,
        confidence: scoreQuery.data?.confidence ?? 'low',
      })
    },
    onSuccess: () => {
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['saved'] })
      toast.success('Look archived to your saved outfits!')
    },
    onError: () => toast.error('Could not archive look. Try again.'),
  })

  const addToCanvas = useCallback((item) => {
    setCanvasItems(prev => {
      if (prev.find(i => i.id === item.id)) return prev
      return [...prev, item]
    })
    setSaved(false)
  }, [])

  const removeFromCanvas = useCallback((itemId) => {
    setCanvasItems(prev => prev.filter(i => i.id !== itemId))
    setSaved(false)
  }, [])

  const handleSwap = useCallback((removeId, addId) => {
    const addItem = items.find(i => i.id === addId)
    if (!addItem) return
    setCanvasItems(prev => prev.map(i => i.id === removeId ? addItem : i))
    setSaved(false)
  }, [items])

  const clearCanvas = useCallback(() => {
    setCanvasItems([])
    setSaved(false)
  }, [])

  function handleDragStart(e, item) {
    e.dataTransfer.setData('application/json', JSON.stringify(item))
    e.dataTransfer.effectAllowed = 'move'
  }

  function handleDrop(e) {
    e.preventDefault()
    try {
      const item = JSON.parse(e.dataTransfer.getData('application/json'))
      addToCanvas(item)
    } catch (_e) { /* ignore malformed drag data */ }
  }

  function handleDragOver(e) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const scoreData = scoreQuery.data
  const isValid = scoreData?.valid
  const pct = isValid ? scoreToPercent(scoreData.final_score) : null

  if (isLoading) return <PageWrapper><LoadingSpinner className="py-16" size="lg" /></PageWrapper>
  if (error) return <PageWrapper><ErrorMessage message="Could not load wardrobe." /></PageWrapper>

  if (items.length < 2) {
    return (
      <PageWrapper>
        <EmptyState
          icon="🎨"
          title="Need more items"
          description="Upload at least 2 wardrobe items to use the outfit editor."
          action={{ label: 'Go to Wardrobe', onClick: () => navigate('/wardrobe') }}
        />
      </PageWrapper>
    )
  }

  return (
    <PageWrapper>
      <div className="mb-8">
        <p className="label-xs mb-1">Creative Suite</p>
        <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
          Outfit Editor
        </h1>
        <p className="text-brand-500 dark:text-brand-400 mt-1">Design and validate your style with AI-powered checks</p>
        {remixItemIds?.length > 0 && (
          <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-50 dark:bg-accent-900/20 border border-accent-200 dark:border-accent-800 text-accent-700 dark:text-accent-300 text-xs font-semibold">
            <span>🔀</span>
            Remix mode — {remixItemIds.length} item{remixItemIds.length !== 1 ? 's' : ''} pre-loaded from the original look
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Sidebar: Wardrobe Assets */}
        <div className="lg:col-span-3 lg:sticky lg:top-24">
          {/* Mobile toggle bar */}
          <button
            onClick={() => setMobileSidebarOpen(o => !o)}
            className="lg:hidden w-full flex items-center justify-between p-4 card-glass mb-3 border-brand-100/60 dark:border-brand-800/40 rounded-2xl"
          >
            <div className="flex items-center gap-2">
              <FiLayers className="text-accent-500" size={16} />
              <span className="font-bold text-sm text-brand-900 dark:text-brand-100">Wardrobe Assets</span>
              <span className="text-xs text-brand-400 dark:text-brand-500">({sidebarItems.length})</span>
            </div>
            <motion.div animate={{ rotate: mobileSidebarOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <FiChevronDown size={16} className="text-brand-400" />
            </motion.div>
          </button>

          <div className={`card-glass p-5 border-brand-100/60 dark:border-brand-800/40 ${mobileSidebarOpen ? 'block' : 'hidden'} lg:block`}>
            <div className="hidden lg:flex items-center gap-2 mb-5">
              <FiLayers className="text-accent-500" size={18} />
              <h2 className="font-display text-lg font-bold text-brand-900 dark:text-brand-100 tracking-tight">Assets</h2>
            </div>

            <div className="flex flex-wrap gap-1.5 mb-5">
              {CATEGORIES.map(cat => {
                const count = cat === 'all'
                  ? items.filter(i => !canvasItemIds.has(i.id)).length
                  : items.filter(i => i.category === cat && !canvasItemIds.has(i.id)).length
                return (
                  <button
                    key={cat}
                    onClick={() => setSidebarFilter(cat)}
                    className={`px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider transition-all border ${
                      sidebarFilter === cat
                        ? 'bg-brand-900 border-brand-900 text-white dark:bg-brand-100 dark:border-brand-100 dark:text-brand-900 shadow-sm'
                        : 'bg-white/40 dark:bg-brand-800/20 text-brand-500 dark:text-brand-400 border-brand-100 dark:border-brand-700 hover:border-brand-300'
                    }`}
                  >
                    {cat}
                  </button>
                )
              })}
            </div>

            <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-2 gap-3 max-h-[40vh] lg:max-h-[50vh] overflow-y-auto pr-1 scrollbar-hide">
              {sidebarItems.map((item, idx) => (
                <motion.div
                  key={item.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, item)}
                  onClick={() => addToCanvas(item)}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: Math.min(idx * 0.03, 0.5) }}
                  className="cursor-grab active:cursor-grabbing group"
                >
                  <div className="aspect-square rounded-2xl overflow-hidden bg-brand-50/60 dark:bg-brand-800/40 border border-brand-100/60 dark:border-brand-700/40 group-hover:border-accent-400 transition-all duration-300 relative shadow-sm">
                    {item.image_url ? (
                      <img src={resolveUrl(item.image_url)} alt={item.category} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-2xl opacity-40 grayscale">
                        {CAT_EMOJI[item.category] || '\u{1F454}'}
                      </div>
                    )}
                    <div className="absolute inset-0 bg-brand-900/0 group-hover:bg-brand-900/5 transition-colors flex items-center justify-center">
                      <FiPlus className="text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-md" size={20} />
                    </div>
                  </div>
                  <p className="text-[9px] font-bold uppercase tracking-widest text-brand-400 text-center mt-1.5 truncate px-1">{item.category}</p>
                </motion.div>
              ))}
              {sidebarItems.length === 0 && (
                <div className="col-span-2 py-10 text-center">
                  <p className="text-[10px] uppercase font-bold tracking-widest text-brand-300">Empty</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Studio Canvas */}
        <div className="lg:col-span-9 space-y-8">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className={`relative min-h-[420px] rounded-[32px] transition-all p-1 shadow-inner-soft border-2 overflow-hidden ${
              canvasItems.length === 0 
                ? 'bg-brand-50/40 dark:bg-brand-900/10 border-dashed border-brand-200 dark:border-brand-700' 
                : 'bg-white dark:bg-brand-900/20 border-brand-100 dark:border-brand-800'
            }`}
          >
            {/* Background Texture */}
            <div className="absolute inset-0 bg-noise opacity-20 pointer-events-none" />
            
            <div className="p-8 relative h-full">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <motion.button
                    onClick={() => setCanvasFullscreen(true)}
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.94 }}
                    title="Expand canvas to fullscreen"
                    className="w-10 h-10 rounded-2xl bg-brand-900 dark:bg-brand-100 flex items-center justify-center text-brand-100 dark:text-brand-900 hover:bg-brand-700 dark:hover:bg-brand-200 transition-colors cursor-pointer"
                  >
                    <FiMaximize2 size={18} />
                  </motion.button>
                  <h2 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 tracking-tight italic">Studio Canvas</h2>
                </div>
                {canvasItems.length > 0 && (
                  <button 
                    onClick={clearCanvas} 
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-[10px] font-bold uppercase tracking-widest hover:bg-red-100 transition-colors"
                  >
                    <FiTrash2 size={12} /> Clear Studio
                  </button>
                )}
              </div>

              {canvasItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="w-20 h-20 rounded-3xl bg-brand-100/40 dark:bg-brand-800/20 flex items-center justify-center text-4xl mb-6 shadow-inner-soft">
                    {'\u{2728}'}
                  </div>
                  <p className="font-display text-xl font-medium text-brand-900 dark:text-brand-200 mb-2">Build Your Vision</p>
                  <p className="text-brand-400 dark:text-brand-500 text-sm max-w-[280px]">
                    <span className="hidden sm:inline">Drag assets from your wardrobe onto the canvas to begin composing.</span>
                    <span className="sm:hidden">Tap items from Wardrobe Assets above to add them to the canvas.</span>
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-4 sm:gap-6">
                  <AnimatePresence mode="popLayout">
                    {canvasItems.map((item, idx) => (
                      <motion.div
                        key={item.id}
                        layout
                        initial={{ opacity: 0, scale: 0.8, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                        className="relative group/item"
                      >
                        <div className="aspect-square rounded-[24px] overflow-hidden bg-white dark:bg-brand-800 border-2 border-brand-100 dark:border-brand-700 shadow-elevated group-hover/item:shadow-card-hover transition-all duration-500 group-hover/item:-translate-y-2">
                          {item.image_url ? (
                            <img src={resolveUrl(item.image_url)} alt={item.category} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-4xl opacity-60">
                              {CAT_EMOJI[item.category] || '👔'}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => removeFromCanvas(item.id)}
                          className="absolute -top-3 -right-3 bg-brand-900 dark:bg-brand-100 text-brand-100 dark:text-brand-900 rounded-full w-8 h-8 flex items-center justify-center opacity-0 group-hover/item:opacity-100 transition-all duration-300 shadow-lg hover:scale-110"
                        >
                          <FiX size={14} />
                        </button>
                        <div className="mt-3 text-center">
                          <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-accent-600 dark:text-accent-400 ml-1">{item.category}</span>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>
          </div>

          {/* Configuration & Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 card-glass p-6">
              <p className="label-xs mb-4">Context Modifiers</p>
              <div className="space-y-5">
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-widest text-brand-400 block mb-2">Occasion</label>
                  <CustomSelect
                    value={occasion}
                    onChange={(val) => { setOccasion(val); setSaved(false) }}
                    options={OCCASIONS}
                  />
                </div>

                <div>
                   <label className="text-[10px] font-bold uppercase tracking-widest text-brand-400 block mb-2">Temperature</label>
                   <div className="flex items-center gap-3">
                      <div className="flex-1">
                        <input
                          type="range"
                          min="-10" max="50"
                          value={tempCelsius}
                          onChange={e => { setTempCelsius(+e.target.value); setSaved(false) }}
                          className="w-full accent-accent-500 h-2 rounded-full appearance-none cursor-pointer bg-brand-200 dark:bg-brand-700"
                          style={{ background: `linear-gradient(to right, var(--color-accent-500) 0%, var(--color-accent-500) ${((tempCelsius + 10) / 60) * 100}%, transparent ${((tempCelsius + 10) / 60) * 100}%)` }}
                        />
                      </div>
                      <span className="data-value text-lg w-12 text-right">{tempCelsius}{'\u00B0'}</span>
                   </div>
                </div>

                <div className="pt-4 border-t border-brand-100/60 dark:border-brand-800/40 flex flex-col gap-2">
                  <button
                    onClick={() => saveMutation.mutate()}
                    disabled={!isValid || saved || saveMutation.isPending}
                    className={`h-11 rounded-2xl transition-all duration-300 flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-widest ${
                      saved
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400 border border-emerald-100/60 dark:border-emerald-800/40'
                        : 'btn-primary disabled:opacity-40 disabled:grayscale'
                    }`}
                  >
                    {saved ? <><FiCheck size={16} /> Saved</> : <><FiBookmark size={16} /> Archive Looks</>}
                  </button>
                  <button
                    onClick={() => setTryOnOpen(true)}
                    disabled={canvasItems.length === 0}
                    className="h-11 rounded-2xl btn-secondary flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-widest disabled:opacity-40"
                  >
                    <FiUser size={16} /> Try On
                  </button>
                  <button
                    onClick={() => navigate('/calendar')}
                    disabled={!isValid}
                    className="h-11 rounded-2xl btn-secondary flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-widest disabled:opacity-40"
                  >
                    <FiCalendar size={16} /> Plan Date
                  </button>
                </div>
              </div>
            </div>

            {/* Validation Panel */}
            <div className="lg:col-span-8 card-glass p-6">
              <div className="flex items-center justify-between mb-6">
                <p className="label-xs">Validation Output</p>
                {scoreQuery.isFetching && <LoadingSpinner size="sm" />}
              </div>

              {canvasItems.length < 2 ? (
                <div className="h-[200px] flex flex-col items-center justify-center text-center opacity-40">
                   <FiCpu size={32} className="mb-4 text-brand-300" />
                   <p className="text-[11px] font-bold uppercase tracking-[0.2em]">Awaiting Analysis</p>
                </div>
              ) : scoreData ? (
                <div className="space-y-6">
                  <div className="flex items-center gap-6">
                    <motion.button
                      onClick={() => setScoreModalOpen(true)}
                      whileHover={{ scale: 1.06 }}
                      whileTap={{ scale: 0.97 }}
                      title="Expand score breakdown"
                      className="relative w-24 h-24 rounded-full border-4 border-brand-50 dark:border-brand-800 flex items-center justify-center bg-white/40 dark:bg-brand-900/20 cursor-pointer group/ring flex-shrink-0"
                    >
                      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 96 96">
                        <circle
                          cx="48" cy="48" r="44"
                          fill="none" strokeWidth="4"
                          className="stroke-brand-50 dark:stroke-brand-800"
                        />
                        <motion.circle
                          cx="48" cy="48" r="44"
                          fill="none" strokeWidth="4"
                          className={`${isValid ? 'stroke-accent-500' : 'stroke-red-500'}`}
                          strokeDasharray="276"
                          initial={{ strokeDashoffset: 276 }}
                          animate={{ strokeDashoffset: 276 - (276 * (pct || 0)) / 100 }}
                          transition={{ duration: 1.5, ease: 'easeOut' }}
                        />
                      </svg>
                      <span className="data-value text-3xl relative z-10 group-hover/ring:opacity-0 transition-opacity duration-150">
                        {isValid ? `${pct}%` : '!!'}
                      </span>
                      <FiMaximize2 size={18} className="absolute opacity-0 group-hover/ring:opacity-100 transition-opacity duration-150 text-brand-600 dark:text-brand-300" />
                    </motion.button>
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                           <h3 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 tracking-tight italic">
                             {isValid ? 'Ready to wear' : 'Critical Mismatch'}
                           </h3>
                           <ConfidenceBadge level={scoreData.confidence} />
                        </div>
                        <p className="text-xs text-brand-500 dark:text-brand-400 font-medium leading-relaxed max-w-[340px]">
                           {isValid 
                             ? "Components are stylistically aligned with specified context and seasonal requirements." 
                             : "Some elements violate core coordination principles. Review the alerts below."}
                        </p>
                    </div>
                  </div>

                  {/* Redesigning violations as premium alerts */}
                  <AnimatePresence>
                    {(scoreData.rule_violations?.length > 0 || scoreData.occasion_mismatches?.length > 0) && (
                      <motion.div 
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="space-y-2"
                      >
                         {scoreData.rule_violations?.map((v, i) => (
                           <div key={i} className="flex iems-center gap-3 p-3 bg-red-50/50 dark:bg-red-900/10 border border-red-100/60 dark:border-red-800/40 rounded-2xl">
                             <FiAlertTriangle className="text-red-500 flex-shrink-0" size={16} />
                             <p className="text-xs font-bold uppercase tracking-tight text-red-700 dark:text-red-400">{v}</p>
                           </div>
                         ))}
                         {scoreData.occasion_mismatches?.map((m, i) => (
                           <div key={i} className="flex items-center gap-3 p-3 bg-amber-50/50 dark:bg-amber-900/10 border border-amber-100/60 dark:border-amber-800/40 rounded-2xl">
                             <FiAlertTriangle className="text-amber-600 flex-shrink-0" size={16} />
                             <p className="text-xs font-bold uppercase tracking-tight text-amber-700 dark:text-amber-400">{m}</p>
                           </div>
                         ))}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {isValid && scoreData.breakdown && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-2">
                      <ScoreStat icon={<FiCpu size={14} />} label="Context" value={scoreData.breakdown.model2_score} />
                      <ScoreStat icon={<FiDroplet size={14} />} label="Chromatic" value={scoreData.breakdown.color_score} />
                      <ScoreStat icon={<FiThermometer size={14} />} label="Climatic" value={scoreData.breakdown.weather_score} />
                    </div>
                  )}

                  {isValid && scoreData.suggestions?.length > 0 && (
                    <SwapSuggestions suggestions={scoreData.suggestions} onSwap={handleSwap} />
                  )}
                </div>
              ) : (
                <ErrorMessage message="Analysis pipeline failed." />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Score Breakdown Modal */}
      <AnimatePresence>
        {scoreModalOpen && scoreData && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-950/50 backdrop-blur-md"
            onClick={() => setScoreModalOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: 'spring', damping: 22, stiffness: 280 }}
              className="card-glass w-full max-w-sm p-8 shadow-elevated border-brand-100/60 dark:border-brand-800/40"
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <p className="label-xs">Score Breakdown</p>
                <button
                  onClick={() => setScoreModalOpen(false)}
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-800 transition-all"
                >
                  <FiX size={16} />
                </button>
              </div>

              {/* Large ring */}
              <div className="flex flex-col items-center mb-8">
                <div className="relative w-36 h-36 flex items-center justify-center">
                  <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 96 96">
                    <circle cx="48" cy="48" r="40" fill="none" strokeWidth="6" className="stroke-brand-100 dark:stroke-brand-800" />
                    <motion.circle
                      cx="48" cy="48" r="40"
                      fill="none" strokeWidth="6"
                      className={isValid ? 'stroke-accent-500' : 'stroke-red-500'}
                      strokeDasharray="251"
                      initial={{ strokeDashoffset: 251 }}
                      animate={{ strokeDashoffset: 251 - (251 * (pct || 0)) / 100 }}
                      transition={{ duration: 1.2, ease: 'easeOut', delay: 0.1 }}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="text-center">
                    <div className="data-value text-4xl leading-none">{isValid ? `${pct}%` : '!!'}</div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-brand-400 mt-1">Match</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <h3 className={`font-display text-lg font-bold tracking-tight italic ${isValid ? 'text-brand-900 dark:text-brand-100' : 'text-red-600 dark:text-red-400'}`}>
                    {isValid ? 'Ready to wear' : 'Critical Mismatch'}
                  </h3>
                  <ConfidenceBadge level={scoreData.confidence} />
                </div>
              </div>

              {/* Score bars */}
              {isValid && scoreData.breakdown && (
                <div className="space-y-4 mb-6">
                  <ScoreStat icon={<FiCpu size={14} />} label="Context" value={scoreData.breakdown.model2_score} delay={0.15} />
                  <ScoreStat icon={<FiDroplet size={14} />} label="Chromatic" value={scoreData.breakdown.color_score} delay={0.25} />
                  <ScoreStat icon={<FiThermometer size={14} />} label="Climatic" value={scoreData.breakdown.weather_score} delay={0.35} />
                </div>
              )}

              {/* Violations */}
              {(scoreData.rule_violations?.length > 0 || scoreData.occasion_mismatches?.length > 0) && (
                <div className="space-y-2 mt-4">
                  {scoreData.rule_violations?.map((v, i) => (
                    <div key={i} className="flex items-start gap-2.5 p-3 bg-red-50/50 dark:bg-red-900/10 border border-red-100/60 dark:border-red-800/40 rounded-xl">
                      <FiAlertTriangle className="text-red-500 flex-shrink-0 mt-0.5" size={14} />
                      <p className="text-xs font-bold uppercase tracking-tight text-red-700 dark:text-red-400">{v}</p>
                    </div>
                  ))}
                  {scoreData.occasion_mismatches?.map((m, i) => (
                    <div key={i} className="flex items-start gap-2.5 p-3 bg-amber-50/50 dark:bg-amber-900/10 border border-amber-100/60 dark:border-amber-800/40 rounded-xl">
                      <FiAlertTriangle className="text-amber-600 flex-shrink-0 mt-0.5" size={14} />
                      <p className="text-xs font-bold uppercase tracking-tight text-amber-700 dark:text-amber-400">{m}</p>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}

        {/* Fullscreen Canvas Modal */}
        {canvasFullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 z-50 flex flex-col bg-white/95 dark:bg-brand-950/95 backdrop-blur-xl"
            onClick={() => setCanvasFullscreen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.97, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 12 }}
              transition={{ type: 'spring', damping: 24, stiffness: 300 }}
              className="flex flex-col h-full"
              onClick={e => e.stopPropagation()}
            >
              {/* Fullscreen header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-brand-100 dark:border-brand-800">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-brand-900 dark:bg-brand-100 flex items-center justify-center text-brand-100 dark:text-brand-900">
                    <FiLayers size={16} />
                  </div>
                  <div>
                    <h2 className="font-display text-xl font-bold text-brand-900 dark:text-brand-100 tracking-tight italic">Studio Canvas</h2>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-brand-400">{canvasItems.length} item{canvasItems.length !== 1 ? 's' : ''}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {scoreData && isValid && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-50 dark:bg-brand-900/40 border border-brand-100 dark:border-brand-800">
                      <span className="data-value text-sm">{pct}%</span>
                      <span className="text-[10px] text-brand-400 font-medium">match</span>
                      <ConfidenceBadge level={scoreData.confidence} />
                    </div>
                  )}
                  <motion.button
                    onClick={() => setCanvasFullscreen(false)}
                    whileHover={{ scale: 1.06 }}
                    whileTap={{ scale: 0.94 }}
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-brand-400 hover:text-brand-700 dark:hover:text-brand-200 hover:bg-brand-100 dark:hover:bg-brand-800 transition-all"
                    title="Exit fullscreen"
                  >
                    <FiMinimize2 size={18} />
                  </motion.button>
                </div>
              </div>

              {/* Fullscreen canvas body */}
              <div className="flex-1 overflow-y-auto p-8">
                {canvasItems.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-24 h-24 rounded-3xl bg-brand-100/40 dark:bg-brand-800/20 flex items-center justify-center text-5xl mb-6">
                      {'\u2728'}
                    </div>
                    <p className="font-display text-2xl font-medium text-brand-900 dark:text-brand-200 mb-2">Canvas is empty</p>
                    <p className="text-brand-400 text-sm">Close fullscreen and add items from your wardrobe.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6 max-w-6xl mx-auto">
                    {canvasItems.map((item) => (
                      <motion.div
                        key={item.id}
                        layout
                        initial={{ opacity: 0, scale: 0.85 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                        className="relative group/fs"
                      >
                        <div className="aspect-square rounded-[28px] overflow-hidden bg-white dark:bg-brand-800 border-2 border-brand-100 dark:border-brand-700 shadow-elevated group-hover/fs:shadow-card-hover group-hover/fs:-translate-y-2 transition-all duration-400">
                          {item.image_url ? (
                            <img src={resolveUrl(item.image_url)} alt={item.category} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-5xl opacity-60">
                              {CAT_EMOJI[item.category] || '👔'}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => removeFromCanvas(item.id)}
                          className="absolute -top-3 -right-3 bg-brand-900 dark:bg-brand-100 text-brand-100 dark:text-brand-900 rounded-full w-8 h-8 flex items-center justify-center opacity-0 group-hover/fs:opacity-100 transition-all duration-300 shadow-lg hover:scale-110"
                        >
                          <FiX size={14} />
                        </button>
                        <div className="mt-3 text-center">
                          <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-accent-600 dark:text-accent-400">{item.category}</span>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <OutfitTryOnModal
        open={tryOnOpen}
        onClose={() => setTryOnOpen(false)}
        items={canvasItems}
        occasion={occasion}
      />
    </PageWrapper>
  )
}

function ScoreStat({ icon, label, value, delay = 0 }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div className="flex flex-col gap-2">
       <div className="flex items-center gap-2 text-brand-400">
         <div className="w-6 h-6 rounded-lg bg-brand-50 dark:bg-brand-800/60 flex items-center justify-center">
            {icon}
         </div>
         <span className="text-[10px] font-bold uppercase tracking-[0.2em]">{label}</span>
       </div>
       <div className="flex items-center gap-3">
          <div className="flex-1 h-3 rounded-full bg-brand-50/60 dark:bg-brand-800/40 shadow-inner overflow-hidden flex items-center p-0.5">
             <motion.div
               initial={{ width: 0 }}
               animate={{ width: `${pct}%` }}
               transition={{ duration: 1, ease: 'easeOut', delay: 0.5 + delay }}
               className={`h-full rounded-full ${pct >= 70 ? 'bg-emerald-500' : pct >= 50 ? 'bg-accent-500' : 'bg-red-400'}`}
             />
          </div>
          <span className="font-mono text-[10px] font-bold text-brand-600 dark:text-brand-300">{pct}%</span>
       </div>
    </div>
  )
}

function SwapSuggestions({ suggestions, onSwap }) {
  return (
    <div className="pt-6 border-t border-brand-100/60 dark:border-brand-800/40">
      <div className="flex items-center gap-2 mb-4">
        <FiZap size={14} className="text-accent-500" />
        <h3 className="text-[10px] font-bold uppercase tracking-[0.25em] text-brand-500">Suggested Optimizations</h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {suggestions.map((s, i) => {
          const delta = Math.round((s.score_delta ?? 0) * 100)
          const imageUrl = s.add_item_image ? resolveUrl(s.add_item_image) : null
          return (
            <motion.button
              key={i}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSwap(s.remove_item_id, s.add_item_id)}
              className="group/swap p-3 rounded-2xl bg-white dark:bg-brand-800/40 border border-brand-100/60 dark:border-brand-700/40 hover:border-accent-200/60 transition-all duration-300 text-left flex items-center gap-4 shadow-sm hover:shadow-md"
            >
              {imageUrl && (
                <div className="w-12 h-12 rounded-xl overflow-hidden bg-brand-50 dark:bg-brand-800 border border-brand-100/60 dark:border-brand-700/40 flex-shrink-0 shadow-sm transition-transform group-hover/swap:scale-105">
                  <img src={imageUrl} alt={s.add_item_category} className="w-full h-full object-cover" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-bold text-brand-900 dark:text-brand-200 leading-tight">
                   {s.add_item_category}
                </p>
                <div className="flex items-center gap-1.5 mt-1">
                   <div className="w-4 h-4 rounded-full bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
                     <FiPlus size={10} className="text-emerald-600 dark:text-emerald-400" />
                   </div>
                   <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">+{delta}% Impact</span>
                </div>
              </div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
