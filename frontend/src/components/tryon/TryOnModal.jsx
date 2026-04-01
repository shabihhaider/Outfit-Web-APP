import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FiX, FiUploadCloud, FiUser, FiRefreshCw, FiCheck, FiAlertTriangle } from 'react-icons/fi'
import { getPersonPhoto, uploadPersonPhoto, submitTryOn, getJobStatus } from '../../api/vto.js'
import LoadingSpinner from '../ui/LoadingSpinner.jsx'

const API_BASE = import.meta.env.VITE_API_URL || ''
const POLL_INTERVAL_MS = 3000

export default function TryOnModal({ open, onClose, item }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)

  const [phase, setPhase] = useState('check')   // check | setup | loading | result | error
  const [jobId, setJobId] = useState(null)
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [previewFile, setPreviewFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [quota, setQuota] = useState({ current: 0, limit: 5 })
  const [pollCount, setPollCount] = useState(0)

  // ── Fetch person photo status ──────────────────────────────────────────────
  const { data: photoData, isLoading: photoLoading } = useQuery({
    queryKey: ['vto-person-photo'],
    queryFn:  getPersonPhoto,
    enabled:  open,
  })

  // ── Reset state when modal closes ─────────────────────────────────────────
  useEffect(() => {
    if (!open) {
      setPhase('check')
      setJobId(null)
      setResult(null)
      setErrorMsg('')
      setPreviewFile(null)
      setPreviewUrl(null)
      setPollCount(0)
    }
  }, [open])

  // ── Determine initial phase once photo status is known ────────────────────
  useEffect(() => {
    if (!open || photoLoading || !photoData) return
    if (photoData.quota) setQuota(photoData.quota)
    if (phase !== 'check') return
    setPhase(photoData.has_photo ? 'ready' : 'setup')
  }, [open, photoLoading, photoData, phase])

  // ── Upload person photo mutation ───────────────────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: uploadPersonPhoto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vto-person-photo'] })
      setPreviewFile(null)
      setPreviewUrl(null)
      setPhase('ready')
    },
    onError: (err) => {
      setErrorMsg(err.response?.data?.error || 'Photo upload failed.')
      setPhase('error')
    },
  })

  // ── Submit try-on job ──────────────────────────────────────────────────────
  const submitMutation = useMutation({
    mutationFn: () => submitTryOn(item.id),
    onSuccess: (data) => {
      if (data.status === 'ready') {
        setResult(data.result_url)
        setPhase('result')
      } else {
        setJobId(data.id)
        setPhase('loading')
        // Optimistically increment or wait for server to report updated quota
        if (data.quota) setQuota(data.quota)
      }
    },
    onError: (err) => {
      const d = err.response?.data
      if (d?.needs_photo) {
        setPhase('setup')
      } else if (err.response?.status === 429) {
        if (d?.quota) setQuota(d.quota)
        setErrorMsg(d?.error || 'Daily limit reached.')
        setPhase('error')
      } else {
        setErrorMsg(d?.error || 'Failed to start try-on.')
        setPhase('error')
      }
    },
  })

  // ── Poll job status ────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'loading' || !jobId) return

    const timer = setTimeout(async () => {
      try {
        const data = await getJobStatus(jobId)
        setPollCount(c => c + 1)

        if (data.status === 'ready') {
          setResult(data.result_url)
          setPhase('result')
        } else if (data.status === 'failed') {
          setErrorMsg(data.error || 'Try-on generation failed.')
          setPhase('error')
        }
        // else still pending/processing — next poll fires from the effect re-run
      } catch {
        setErrorMsg('Lost connection while waiting. Please try again.')
        setPhase('error')
      }
    }, POLL_INTERVAL_MS)

    return () => clearTimeout(timer)
  }, [phase, jobId, pollCount])

  // ── File select ───────────────────────────────────────────────────────────
  const handleFileSelect = useCallback((f) => {
    if (!f) return
    setPreviewFile(f)
    setPreviewUrl(URL.createObjectURL(f))
    setErrorMsg('')
  }, [])

  function handlePhotoSubmit() {
    if (!previewFile) return
    const fd = new FormData()
    fd.append('photo', previewFile)
    uploadMutation.mutate(fd)
  }

  if (!open || !item) return null

  const itemImageUrl = item.image_url ? `${API_BASE}${item.image_url}` : null
  const personPhotoUrl = photoData?.photo_url ? `${API_BASE}${photoData.photo_url}` : null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-950/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="card w-full max-w-lg shadow-modal max-h-[92vh] overflow-y-auto"
          onClick={e => e.stopPropagation()}
        >
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="font-display text-2xl font-semibold text-brand-900 dark:text-brand-100">
                  Virtual Try-On
                </h2>
                <p className="text-xs text-brand-400 dark:text-brand-500 mt-0.5">
                  Powered by IDM-VTON · AI Diffusion
                </p>
              </div>
              <button onClick={onClose} className="p-1.5 rounded-lg text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors">
                <FiX size={18} />
              </button>
            </div>

            {/* ── Phase: check / loading screen ── */}
            {(phase === 'check' || photoLoading) && (
              <div className="py-12 flex flex-col items-center gap-3 text-brand-400">
                <LoadingSpinner size="md" />
                <p className="text-sm">Checking your profile...</p>
              </div>
            )}

            {/* ── Phase: setup (no person photo yet) ── */}
            {phase === 'setup' && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <div className="mb-5 p-4 rounded-2xl bg-accent-50/60 dark:bg-accent-900/20 border border-accent-200/50 dark:border-accent-700/30">
                  <div className="flex items-start gap-3">
                    <FiUser className="text-accent-500 mt-0.5 shrink-0" size={18} />
                    <div>
                      <p className="text-sm font-medium text-accent-700 dark:text-accent-300">
                        One-time setup required
                      </p>
                      <p className="text-xs text-accent-600/80 dark:text-accent-400/80 mt-1">
                        Upload a clear photo of yourself. It will be reused for all future try-ons — you only need to do this once.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Photo tips */}
                <ul className="space-y-1.5 mb-5">
                  {[
                    'Stand against a plain wall or background',
                    'Full-body or torso shot works best',
                    'Face the camera directly in a neutral pose',
                    'Good lighting — no harsh shadows',
                  ].map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-brand-500 dark:text-brand-400">
                      <span className="text-accent-400 font-bold mt-0.5">·</span>
                      {tip}
                    </li>
                  ))}
                </ul>

                {/* Drop zone */}
                <div
                  className="border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200 border-brand-200 dark:border-brand-700 hover:border-accent-300 dark:hover:border-accent-600 overflow-hidden mb-4"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {previewUrl ? (
                    <div className="relative">
                      <img src={previewUrl} alt="Preview" className="w-full h-56 object-cover" />
                      <div className="absolute inset-0 bg-brand-900/30 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                        <span className="text-white text-sm font-medium bg-black/30 px-3 py-1.5 rounded-lg backdrop-blur-sm">Change photo</span>
                      </div>
                    </div>
                  ) : (
                    <div className="py-12 flex flex-col items-center text-brand-400 dark:text-brand-500">
                      <FiUser size={32} className="mb-3 text-brand-300 dark:text-brand-600" />
                      <p className="text-sm font-medium">Upload your photo</p>
                      <p className="text-xs mt-1">JPG or PNG</p>
                    </div>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={e => handleFileSelect(e.target.files[0])}
                  />
                </div>

                {errorMsg && (
                  <div className="mb-4 p-3 bg-red-50/80 dark:bg-red-900/15 border border-red-200/60 dark:border-red-800/40 rounded-xl text-red-700 dark:text-red-300 text-sm">
                    {errorMsg}
                  </div>
                )}

                <div className="flex gap-3">
                  <button onClick={onClose} className="flex-1 btn-secondary">Cancel</button>
                  <button
                    onClick={handlePhotoSubmit}
                    disabled={!previewFile || uploadMutation.isPending}
                    className="flex-1 btn-primary flex items-center justify-center gap-2"
                  >
                    {uploadMutation.isPending
                      ? <><LoadingSpinner size="sm" /> Uploading...</>
                      : <><FiUploadCloud size={15} /> Save & Continue</>
                    }
                  </button>
                </div>
              </motion.div>
            )}

            {/* ── Phase: ready (has person photo — confirm and submit) ── */}
            {phase === 'ready' && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {/* Person photo */}
                  <div>
                    <p className="label-xs mb-2">Your photo</p>
                    <div className="aspect-[3/4] rounded-2xl overflow-hidden bg-brand-100 dark:bg-brand-800 border border-brand-200/60 dark:border-brand-700/40">
                      {personPhotoUrl
                        ? <img src={personPhotoUrl} alt="You" className="w-full h-full object-cover" />
                        : <div className="w-full h-full flex items-center justify-center text-brand-400"><FiUser size={32} /></div>
                      }
                    </div>
                  </div>

                  {/* Garment */}
                  <div>
                    <p className="label-xs mb-2">{item.category} to try</p>
                    <div className="aspect-[3/4] rounded-2xl overflow-hidden bg-brand-50 dark:bg-brand-800/60 border border-brand-200/60 dark:border-brand-700/40">
                      {itemImageUrl
                        ? <img src={itemImageUrl} alt={item.category} className="w-full h-full object-cover" />
                        : <div className="w-full h-full flex items-center justify-center text-brand-400 text-4xl">👕</div>
                      }
                    </div>
                  </div>
                </div>

                <p className="text-xs text-brand-400 dark:text-brand-500 text-center mb-5">
                  AI will digitally place this item on your photo using IDM-VTON diffusion model.
                  First try takes ~60–90 seconds; subsequent tries are instant from cache.
                </p>

                <div className="flex gap-3">
                  <button
                    onClick={() => setPhase('setup')}
                    className="btn-secondary flex items-center gap-2"
                    title="Change person photo"
                  >
                    <FiRefreshCw size={14} /> Change photo
                  </button>
                  <button
                    onClick={() => submitMutation.mutate()}
                    disabled={submitMutation.isPending || quota.current >= quota.limit}
                    className="flex-1 btn-primary flex items-center justify-center gap-2 relative"
                  >
                    {submitMutation.isPending
                      ? <><LoadingSpinner size="sm" /> Starting...</>
                      : (
                        <>
                          <span className="flex-1 text-center">Generate Try-On</span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            quota.current >= quota.limit
                              ? 'bg-red-500/20 text-red-500' 
                              : 'bg-brand-900/40 text-brand-200'
                          }`}>
                            {quota.current} / {quota.limit}
                          </span>
                        </>
                      )
                    }
                  </button>
                </div>
                {quota.current >= quota.limit && (
                   <p className="text-[10px] text-red-500 text-center mt-2 font-medium">
                     Daily quota reached. Please try again tomorrow.
                   </p>
                )}
              </motion.div>
            )}

            {/* ── Phase: loading (job submitted, polling) ── */}
            {phase === 'loading' && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="py-8 flex flex-col items-center text-center"
              >
                {/* Animated garment preview */}
                <div className="relative w-24 h-24 mb-6">
                  <motion.div
                    animate={{ scale: [1, 1.04, 1], opacity: [0.8, 1, 0.8] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    className="w-24 h-24 rounded-2xl overflow-hidden border-2 border-accent-200 dark:border-accent-700 shadow-lg"
                  >
                    {itemImageUrl
                      ? <img src={itemImageUrl} alt={item.category} className="w-full h-full object-cover" />
                      : <div className="w-full h-full flex items-center justify-center text-4xl bg-brand-100 dark:bg-brand-800">👕</div>
                    }
                  </motion.div>
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-accent-500 flex items-center justify-center shadow-md">
                    <LoadingSpinner size="sm" color="white" />
                  </div>
                </div>

                <p className="font-display text-lg font-semibold text-brand-900 dark:text-brand-100 mb-2">
                  Atelier is working...
                </p>
                <p className="text-sm text-brand-500 dark:text-brand-400 mb-1">
                  IDM-VTON diffusion model is generating your try-on
                </p>
                <p className="text-xs text-brand-400 dark:text-brand-500">
                  This takes about 60–90 seconds on first try
                </p>

                {/* Progress steps */}
                <div className="mt-6 space-y-2 w-full max-w-xs text-left">
                  {[
                    { label: 'Segmenting your photo',           done: pollCount >= 2 },
                    { label: 'Warping garment to body shape',   done: pollCount >= 5 },
                    { label: 'Diffusion refinement (shadows, folds)', done: pollCount >= 8 },
                    { label: 'Finalizing result',               done: false },
                  ].map((step, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 transition-all duration-500 ${
                        step.done
                          ? 'bg-emerald-500'
                          : 'border-2 border-brand-200 dark:border-brand-700'
                      }`}>
                        {step.done && <FiCheck size={9} className="text-white" />}
                      </div>
                      <span className={`text-xs transition-colors ${
                        step.done
                          ? 'text-brand-600 dark:text-brand-300 font-medium'
                          : 'text-brand-400 dark:text-brand-500'
                      }`}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* ── Phase: result ── */}
            {phase === 'result' && result && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <div className="mb-4 rounded-2xl overflow-hidden border border-brand-200/60 dark:border-brand-700/40 shadow-md bg-white dark:bg-brand-800">
                  <img
                    src={`${API_BASE}${result}`}
                    alt="Virtual try-on result"
                    className="w-full object-contain max-h-[50vh]"
                  />
                </div>
                <div className="flex items-center gap-2 mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200/60 dark:border-emerald-700/30">
                  <FiCheck className="text-emerald-500 shrink-0" size={15} />
                  <p className="text-xs text-emerald-700 dark:text-emerald-300">
                    Generated by IDM-VTON · Result cached — try-on again instantly
                  </p>
                </div>
                <div className="flex gap-3">
                  <button onClick={onClose} className="flex-1 btn-secondary">Close</button>
                  <a
                    href={`${API_BASE}${result}`}
                    download={`tryon_${item.category}.png`}
                    className="flex-1 btn-primary text-center flex items-center justify-center gap-2"
                  >
                    Download
                  </a>
                </div>
              </motion.div>
            )}

            {/* ── Phase: error ── */}
            {phase === 'error' && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <div className="py-4 text-center mb-5">
                  <div className="w-14 h-14 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
                    <FiAlertTriangle className="text-red-500" size={24} />
                  </div>
                  <p className="font-medium text-brand-800 dark:text-brand-200 mb-2">Try-on failed</p>
                  <p className="text-sm text-brand-500 dark:text-brand-400">
                    {errorMsg || 'Something went wrong. The HF Space may be temporarily unavailable.'}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button onClick={onClose} className="flex-1 btn-secondary">Close</button>
                  <button
                    onClick={() => { setPhase('ready'); setErrorMsg('') }}
                    className="flex-1 btn-primary flex items-center justify-center gap-2"
                  >
                    <FiRefreshCw size={14} /> Try again
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
