import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiShield, FiX } from 'react-icons/fi'
import { getConsent, updateConsent } from '../../api/auth.js'
import { useAuth } from '../../context/AuthContext.jsx'

export default function ConsentBanner() {
  const { isAuthenticated } = useAuth()
  const qc = useQueryClient()
  const [dismissed, setDismissed] = useState(false)

  const [pendingAction, setPendingAction] = useState(null) // 'accept' | 'decline'

  const { data } = useQuery({
    queryKey: ['user-consent'],
    queryFn: getConsent,
    enabled: isAuthenticated,
    staleTime: Infinity,   // decision is permanent for session; don't re-fetch on navigation
    gcTime: Infinity,
  })

  const mutation = useMutation({
    mutationFn: updateConsent,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-consent'] })
      setDismissed(true)
      setPendingAction(null)
    },
    onError: () => setPendingAction(null),
  })

  // Don't show if not authenticated, already dismissed, or consent already set
  if (!isAuthenticated || dismissed || !data?.consents) return null

  const consents = data.consents
  // hasDecided: any consent was explicitly set (granted true OR false) or previously revoked
  const hasDecided = Object.values(consents).some(
    c => c.granted === true || c.granted === false || c.revoked_at
  )
  if (hasDecided) return null

  function handleAcceptAll() {
    const payload = {}
    for (const key of Object.keys(consents)) payload[key] = true
    setPendingAction('accept')
    mutation.mutate(payload)
  }

  function handleDeclineAll() {
    const payload = {}
    for (const key of Object.keys(consents)) payload[key] = false
    setPendingAction('decline')
    mutation.mutate(payload)
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 40 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 sm:max-w-md z-50"
      >
        <div className="bg-white dark:bg-brand-900 border border-brand-200 dark:border-brand-700 rounded-2xl shadow-elevated p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center flex-shrink-0">
                <FiShield size={16} className="text-accent-700 dark:text-accent-400" />
              </div>
              <h3 className="font-semibold text-sm text-brand-800 dark:text-brand-200">Data Usage Consent</h3>
            </div>
            <button
              onClick={() => setDismissed(true)}
              className="p-1 text-brand-500 hover:text-brand-600 dark:hover:text-brand-300 transition-colors"
            >
              <FiX size={16} />
            </button>
          </div>

          <p className="text-xs text-brand-500 dark:text-brand-400 leading-relaxed">
            OutfitAI would like to use your wardrobe data and preferences to improve our AI models and app experience.
            You can review and change these settings anytime in <span className="font-medium text-brand-700 dark:text-brand-300">Settings &gt; Privacy</span>.
          </p>

          <div className="flex gap-2">
            <button
              onClick={handleDeclineAll}
              disabled={mutation.isPending}
              className="flex-1 h-9 rounded-xl border border-brand-200 dark:border-brand-700 text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-800 transition-colors disabled:opacity-50"
            >
              {pendingAction === 'decline' ? 'Saving...' : 'Decline'}
            </button>
            <button
              onClick={handleAcceptAll}
              disabled={mutation.isPending}
              className="flex-1 h-9 rounded-xl bg-accent-500 text-white text-sm font-medium hover:bg-accent-600 transition-colors disabled:opacity-50"
            >
              {pendingAction === 'accept' ? 'Saving...' : 'Accept All'}
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
