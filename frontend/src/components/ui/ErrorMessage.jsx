import { FiAlertCircle } from 'react-icons/fi'

export default function ErrorMessage({ message, onRetry }) {
  return (
    <div role="alert" className="rounded-xl bg-red-50/80 dark:bg-red-900/15 border border-red-200/60 dark:border-red-800/40 p-4 flex items-start gap-3">
      <FiAlertCircle className="text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" size={16} />
      <div className="flex-1">
        <p className="text-red-700 dark:text-red-300 text-sm font-medium">{message || 'Something went wrong.'}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium transition-colors"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}
