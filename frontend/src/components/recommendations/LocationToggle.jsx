import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiNavigation } from 'react-icons/fi'
import LoadingSpinner from '../ui/LoadingSpinner.jsx'

export default function LocationToggle({ onTempChange }) {
  const [useLocation, setUseLocationRaw] = useState(() => sessionStorage.getItem('rec_useLocation') === 'true')
  const [manualTemp, setManualTemp] = useState(() => {
    const saved = sessionStorage.getItem('rec_manualTemp')
    return saved ? Number(saved) : 25
  })
  const [locStatus, setLocStatus] = useState('')
  const [locLoading, setLocLoading] = useState(false)
  const didInit = useRef(false)

  function setUseLocation(val) {
    setUseLocationRaw(val)
    sessionStorage.setItem('rec_useLocation', String(val))
  }

  useEffect(() => {
    if (didInit.current) return
    didInit.current = true
    if (useLocation) {
      requestLocation()
    } else {
      onTempChange({ temp_celsius: manualTemp })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function requestLocation() {
    setLocLoading(true)
    setLocStatus('Syncing location...')
    navigator.geolocation.getCurrentPosition(
      pos => {
        const { latitude, longitude } = pos.coords
        onTempChange({ lat: latitude, lon: longitude })
        setLocStatus('Location synchronized')
        setLocLoading(false)
      },
      () => {
        setUseLocation(false)
        setLocStatus('Access denied \u2014 using manual')
        onTempChange({ temp_celsius: manualTemp })
        setLocLoading(false)
      }
    )
  }

  function handleToggle() {
    const next = !useLocation
    setUseLocation(next)
    if (!next) {
      onTempChange({ temp_celsius: manualTemp })
      setLocStatus('')
    } else {
      requestLocation()
    }
  }

  function handleSlider(e) {
    const val = Number(e.target.value)
    setManualTemp(val)
    sessionStorage.setItem('rec_manualTemp', String(val))
    if (!useLocation) onTempChange({ temp_celsius: val })
  }

  return (
    <div className="card-glass p-6">
      <p className="label-xs mb-4">Climate Control</p>
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">Weather</h3>
        <button
          onClick={handleToggle}
          type="button"
          role="switch"
          aria-checked={useLocation}
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-all duration-300 focus-ring ${
            useLocation ? 'bg-accent-500' : 'bg-brand-200 dark:bg-brand-700'
          }`}
        >
          <motion.span 
            animate={{ x: useLocation ? 24 : 4 }}
            className="inline-block h-4 w-4 rounded-full bg-white shadow-sm" 
          />
        </button>
      </div>

      <div className="space-y-4">
        {/* Location Status */}
        <AnimatePresence mode="wait">
          {(locLoading || locStatus) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="flex items-center gap-3 p-3 bg-brand-50/60 dark:bg-brand-800/30 border border-brand-100/40 dark:border-brand-700/40 rounded-xl">
                {locLoading ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-brand-100 dark:bg-brand-700 flex items-center justify-center">
                    <FiNavigation size={10} className="text-brand-600 dark:text-brand-300" />
                  </div>
                )}
                <p className="text-xs font-medium text-brand-600 dark:text-brand-400">{locStatus}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Manual control */}
        <div className={`transition-all duration-500 ${useLocation ? 'opacity-40 grayscale pointer-events-none' : 'opacity-100'}`}>
          <div className="flex justify-between items-end mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-brand-500">Manual Temperature</span>
            <span className="data-value text-lg leading-none">{manualTemp}°C</span>
          </div>
          <input
            type="range"
            min="0" max="50"
            value={manualTemp}
            onChange={handleSlider}
            className="w-full"
          />
          <div className="flex justify-between text-[10px] font-mono text-brand-500 dark:text-brand-400 mt-2">
            <span>0°C</span>
            <span>50°C</span>
          </div>
        </div>
      </div>
    </div>
  )
}
