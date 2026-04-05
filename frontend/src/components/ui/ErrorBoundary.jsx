import { Component } from 'react'
import { FiAlertTriangle, FiRefreshCw } from 'react-icons/fi'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-5">
            <FiAlertTriangle size={28} className="text-red-500" />
          </div>
          <h2 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-brand-500 dark:text-brand-400 mb-6">
            An unexpected error occurred. Please refresh the page to try again.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="btn-primary inline-flex items-center gap-2"
          >
            <FiRefreshCw size={14} />
            Refresh Page
          </button>
        </div>
      </div>
    )
  }
}
