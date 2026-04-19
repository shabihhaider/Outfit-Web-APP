import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiChevronDown, FiCheck } from 'react-icons/fi'

export default function CustomSelect({ value, onChange, options, label, className = '' }) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)

  const selectedOption = options.find(opt => opt.value === value) || options[0]

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {label && (
        <label className="text-[10px] font-bold uppercase tracking-widest text-brand-500 mb-2 block">
          {label}
        </label>
      )}
      
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-brand-50/50 dark:bg-brand-800/20 border border-brand-100/60 dark:border-brand-700/40 text-sm font-medium text-brand-900 dark:text-brand-100 transition-all hover:bg-white dark:hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-accent-500/20"
      >
        <span className="capitalize">{selectedOption.label}</span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <FiChevronDown className="text-brand-500" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.ul
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 4, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="absolute z-50 w-full p-2 rounded-2xl bg-white/90 dark:bg-brand-800/95 backdrop-blur-xl border border-brand-100/80 dark:border-brand-700/60 shadow-elevated max-h-60 overflow-y-auto"
          >
            {options.map(option => (
              <li key={option.value}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(option.value)
                    setIsOpen(false)
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition-all ${
                    value === option.value
                      ? 'bg-brand-900 text-white dark:bg-brand-100 dark:text-brand-900'
                      : 'text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-700/50'
                  }`}
                >
                  <span className="capitalize">{option.label}</span>
                  {value === option.value && <FiCheck size={14} />}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
