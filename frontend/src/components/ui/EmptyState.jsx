import { motion } from 'framer-motion'

export default function EmptyState({ icon = '', title, description, action }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col items-center justify-center py-20 px-4 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-brand-100/80 dark:bg-brand-800/40 flex items-center justify-center text-3xl mb-5">
        {icon}
      </div>
      <h3 className="font-display text-2xl font-semibold text-brand-700 dark:text-brand-300 mb-2">{title}</h3>
      {description && (
        <p className="text-brand-500 dark:text-brand-400 text-sm max-w-sm mb-8 leading-relaxed">{description}</p>
      )}
      {action && (
        <button onClick={action.onClick} className="btn-primary">
          {action.label}
        </button>
      )}
    </motion.div>
  )
}
