import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { motion, AnimatePresence } from 'framer-motion'
import { FiArrowRight, FiUploadCloud, FiZap, FiStar } from 'react-icons/fi'
import UploadModal from '../wardrobe/UploadModal.jsx'
import { useQuery } from '@tanstack/react-query'
import { getItems } from '../../api/wardrobe.js'

const TOTAL_STEPS = 4

// Static demo outfit — no backend, no images required
const DEMO_OUTFIT = {
  items: [
    { category: 'top',    emoji: '👔', label: 'Oxford Shirt',   color: 'bg-sky-100 dark:bg-sky-900/30' },
    { category: 'bottom', emoji: '👖', label: 'Chino Trousers', color: 'bg-stone-100 dark:bg-stone-800/40' },
    { category: 'shoes',  emoji: '👞', label: 'Leather Loafers', color: 'bg-amber-100 dark:bg-amber-900/30' },
  ],
  finalScore: 0.87,
  model2_score:   0.91,
  synergy_score:  0.80,
  color_score:    0.85,
  cohesion_score: 0.88,
  weather_score:  0.82,
  occasion: 'Smart Casual',
}

function pct(v) { return Math.round((v ?? 0) * 100) }

function DemoScoreBar({ label, value, weight }) {
  const p = pct(value)
  const color = p >= 70 ? 'bg-emerald-500' : p >= 50 ? 'bg-accent-500' : 'bg-red-500'
  return (
    <div>
      <div className="flex justify-between text-[11px] text-brand-500 dark:text-brand-400 mb-1">
        <span>{label}</span>
        <span className="font-mono font-semibold">{p}%</span>
      </div>
      <div className="h-1.5 bg-brand-200/60 dark:bg-brand-700/40 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${color} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${p}%` }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.3 }}
        />
      </div>
      {weight && <div className="text-[9px] text-brand-300 dark:text-brand-600 mt-0.5 text-right">{weight} weight</div>}
    </div>
  )
}

export default function OnboardingFlow() {
  const [step, setStep] = useState(1)
  const [uploadOpen, setUploadOpen] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (localStorage.getItem('onboarding_done') === '1') {
      navigate('/dashboard', { replace: true })
    }
  }, [navigate])

  const { data } = useQuery({
    queryKey: ['wardrobe'],
    queryFn: getItems,
    refetchInterval: 3000,
  })
  const itemCount = data?.items?.length ?? 0

  function finish() {
    localStorage.setItem('onboarding_done', '1')
    navigate('/dashboard', { replace: true })
  }

  return (
    <>
      <div className="min-h-screen bg-brand-50 dark:bg-brand-950 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Progress */}
          <div className="flex justify-center gap-2 mb-8">
            {Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).map(s => (
              <motion.div
                key={s}
                animate={{ width: s === step ? 32 : 8 }}
                className={`h-2 rounded-full transition-colors duration-300 ${
                  s === step ? 'bg-brand-900 dark:bg-brand-100' : s < step ? 'bg-brand-400 dark:bg-brand-500' : 'bg-brand-200 dark:bg-brand-700'
                }`}
              />
            ))}
          </div>

          <AnimatePresence mode="wait">
            {/* Step 1: Welcome */}
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="card p-8 shadow-elevated text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-brand-900 dark:bg-brand-100 flex items-center justify-center mx-auto mb-6">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" className="text-white dark:text-brand-900">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <h2 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 mb-3">
                  Welcome, {user?.name}!
                </h2>
                <p className="text-brand-500 dark:text-brand-400 mb-8 leading-relaxed">
                  Let&apos;s set up your wardrobe so AI can recommend outfits tailored to your style.
                </p>
                <button onClick={() => setStep(2)} className="btn-primary w-full py-3 text-base flex items-center justify-center gap-2 group">
                  Get Started <FiArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
                </button>
              </motion.div>
            )}

            {/* Step 2: Demo */}
            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="card p-6 shadow-elevated"
              >
                <div className="flex items-center gap-2 mb-1">
                  <FiStar size={14} className="text-accent-500" />
                  <span className="label-xs text-accent-600 dark:text-accent-400">Preview</span>
                </div>
                <h2 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 mb-1">
                  See what OutfitAI does
                </h2>
                <p className="text-sm text-brand-500 dark:text-brand-400 mb-5 leading-relaxed">
                  Complete outfits scored by style compatibility, color harmony, and weather suitability — built from your wardrobe.
                </p>

                {/* Demo outfit card */}
                <div className="bg-brand-50/60 dark:bg-brand-800/30 rounded-2xl p-4 mb-5">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-medium text-brand-500 dark:text-brand-400">{DEMO_OUTFIT.occasion}</span>
                    <div className="flex items-center gap-1.5 bg-brand-900 dark:bg-brand-100 text-white dark:text-brand-900 rounded-full px-2.5 py-1">
                      <FiStar size={10} />
                      <span className="text-xs font-bold">{pct(DEMO_OUTFIT.finalScore)}% Match</span>
                    </div>
                  </div>

                  {/* Item thumbnails */}
                  <div className="flex gap-2 mb-4">
                    {DEMO_OUTFIT.items.map((item, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                        <div className={`w-full aspect-square rounded-xl ${item.color} flex items-center justify-center text-3xl border border-brand-100/60 dark:border-brand-700/40`}>
                          {item.emoji}
                        </div>
                        <span className="text-[10px] text-brand-500 dark:text-brand-400 text-center leading-tight">{item.label}</span>
                      </div>
                    ))}
                  </div>

                  {/* Score breakdown */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 pt-3 border-t border-brand-100/60 dark:border-brand-700/40">
                    <DemoScoreBar label="Style"    value={DEMO_OUTFIT.model2_score}   weight="35%" />
                    <DemoScoreBar label="Synergy"  value={DEMO_OUTFIT.synergy_score}  weight="20%" />
                    <DemoScoreBar label="Color"    value={DEMO_OUTFIT.color_score}    weight="20%" />
                    <DemoScoreBar label="Weather"  value={DEMO_OUTFIT.weather_score}  weight="15%" />
                    <DemoScoreBar label="Cohesion" value={DEMO_OUTFIT.cohesion_score} weight="10%" />
                  </div>
                </div>

                <button
                  onClick={() => setStep(3)}
                  className="btn-primary w-full py-3 text-base flex items-center justify-center gap-2 group mb-3"
                >
                  Build my wardrobe <FiArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="w-full text-center text-sm text-brand-500 hover:text-brand-600 dark:hover:text-brand-300 py-2 transition-colors"
                >
                  Skip preview
                </button>
              </motion.div>
            )}

            {/* Step 3: Upload */}
            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="card p-8 shadow-elevated"
              >
                <h2 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 mb-2">Upload your clothes</h2>
                <p className="text-brand-500 dark:text-brand-400 mb-6 leading-relaxed">
                  Upload at least 3 items to get your first recommendation. AI detects the category automatically.
                </p>

                <div className="mb-6">
                  <div className="flex justify-between text-sm text-brand-600 dark:text-brand-400 mb-2">
                    <span>Items uploaded</span>
                    <span className="data-value text-sm">{itemCount} / 3</span>
                  </div>
                  <div className="h-2.5 bg-brand-100/60 dark:bg-brand-800/40 rounded-full overflow-hidden">
                    <motion.div
                      animate={{ width: `${Math.min(100, (itemCount / 3) * 100)}%` }}
                      className="h-full bg-brand-900 dark:bg-brand-100 rounded-full"
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </div>

                <button onClick={() => setUploadOpen(true)} className="btn-primary w-full mb-3 flex items-center justify-center gap-2">
                  <FiUploadCloud size={16} /> Upload Item
                </button>

                {itemCount >= 3 && (
                  <button onClick={() => setStep(4)} className="btn-secondary w-full flex items-center justify-center gap-2 group">
                    Continue <FiArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                  </button>
                )}

                <button onClick={() => setStep(4)} className="w-full text-center text-sm text-brand-500 hover:text-brand-600 dark:hover:text-brand-300 mt-4 py-2 transition-colors">
                  Skip for now
                </button>
              </motion.div>
            )}

            {/* Step 4: Done */}
            {step === 4 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="card p-8 shadow-elevated text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-6 text-3xl">
                  {'🎉'}
                </div>
                <h2 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 mb-3">You&apos;re all set!</h2>
                <p className="text-brand-500 dark:text-brand-400 mb-8 leading-relaxed">
                  Your wardrobe is ready. Let&apos;s find your first perfect outfit.
                </p>
                <button
                  onClick={() => { localStorage.setItem('onboarding_done', '1'); navigate('/recommendations', { replace: true }) }}
                  className="btn-primary w-full py-3 text-base mb-3 flex items-center justify-center gap-2 group"
                >
                  <FiZap size={16} /> Get Recommendations
                </button>
                <button onClick={finish} className="btn-secondary w-full">
                  Go to Dashboard
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  )
}
