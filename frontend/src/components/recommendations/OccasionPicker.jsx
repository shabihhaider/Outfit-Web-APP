import { motion } from 'framer-motion'
import { FiSun, FiBriefcase } from 'react-icons/fi'

const OCCASIONS = [
  { value: 'casual', label: 'Casual', desc: 'Everyday', icon: FiSun },
  { value: 'formal', label: 'Formal', desc: 'Professional', icon: FiBriefcase },
]

export default function OccasionPicker({ value, onChange }) {
  return (
    <div className="card-glass p-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <p className="label-xs mb-1">Style Context</p>
          <h3 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 tracking-tight italic">
            Choose Occasion
          </h3>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {OCCASIONS.map(occ => (
          <motion.button
            key={occ.value}
            whileHover={{ y: -4, scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onChange(occ.value)}
            className={`group relative p-6 rounded-[28px] text-left transition-all duration-500 border-2 overflow-hidden ${
              value === occ.value
                ? 'bg-brand-900 border-brand-900 text-white dark:bg-brand-100 dark:border-brand-100 dark:text-brand-900 shadow-elevated'
                : 'bg-white/40 dark:bg-brand-800/10 border-brand-100/40 dark:border-brand-700/30 text-brand-600 dark:text-brand-400 hover:border-brand-300 dark:hover:border-brand-600'
            }`}
          >
            {/* Background Grain Accent */}
            {value === occ.value && (
              <div className="absolute inset-0 bg-noise opacity-[0.05] pointer-events-none" />
            )}
            
            <div className={`mb-6 w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-500 shadow-sm ${
              value === occ.value 
                ? 'bg-white/10 text-white dark:bg-brand-900/10 dark:text-brand-900 rotate-12' 
                : 'bg-brand-50 dark:bg-brand-800/40 text-brand-500 group-hover:rotate-12'
            }`}>
              <occ.icon size={22} />
            </div>
            
            <div className="space-y-1 relative z-10">
              <div className="font-display text-xl font-bold tracking-tight leading-none">
                {occ.label}
              </div>
              <div className={`text-[10px] uppercase tracking-[0.2em] font-bold opacity-50`}>
                {occ.desc}
              </div>
            </div>
            
            {/* Active Indicator Pulse */}
            {value === occ.value && (
              <motion.div 
                layoutId="active-indicator"
                className="absolute top-4 right-4 w-2 h-2 rounded-full bg-accent-500"
              />
            )}
          </motion.button>
        ))}
      </div>
    </div>
  )
}
