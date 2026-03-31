import { motion, AnimatePresence } from 'framer-motion'

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel, danger = false }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-950/40 backdrop-blur-sm"
          onClick={onCancel}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="card p-6 w-full max-w-sm shadow-modal"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="font-display text-2xl font-semibold text-brand-900 dark:text-brand-100 mb-2">{title}</h3>
            <p className="text-brand-500 dark:text-brand-400 text-sm mb-6 leading-relaxed">{message}</p>
            <div className="flex gap-3 justify-end">
              <button onClick={onCancel} className="btn-secondary text-sm">Cancel</button>
              <button
                onClick={onConfirm}
                className={danger ? 'btn-danger text-sm' : 'btn-primary text-sm'}
              >
                Confirm
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
