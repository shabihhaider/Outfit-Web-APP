import { motion } from 'framer-motion'
import { FiThermometer, FiMapPin } from 'react-icons/fi'

export default function WeatherCard({ detectedTemp, locationName }) {
  if (detectedTemp === null) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="card-glass p-5 flex items-center gap-5 border-accent-200/40 dark:border-accent-800/20 bg-accent-50/30 dark:bg-accent-950/20"
    >
      <div className="w-12 h-12 rounded-2xl bg-accent-100/60 dark:bg-accent-900/30 flex items-center justify-center shadow-sm">
        <FiThermometer className="text-accent-600 dark:text-accent-400" size={22} />
      </div>
      
      <div className="flex-1">
        <div className="flex items-baseline gap-1.5">
          <span className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
            {detectedTemp}{'\u00B0'}
          </span>
          <span className="text-[11px] font-bold uppercase tracking-widest text-brand-400 dark:text-brand-500 mb-1">
            Celsius
          </span>
        </div>
        
        <div className="flex items-center gap-1.5 mt-0.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <p className="text-[10px] font-bold uppercase tracking-widest text-accent-700/70 dark:text-accent-400/60 flex items-center gap-1">
            <FiMapPin size={10} /> {locationName || 'Local Sync'}
          </p>
        </div>
      </div>
      
      <div className="hidden sm:block h-10 w-[1px] bg-brand-200/50 dark:bg-brand-700/30 mx-2" />
      
      <div className="hidden sm:block text-right">
        <p className="text-[10px] font-bold uppercase tracking-widest text-brand-400">Status</p>
        <p className="text-xs font-semibold text-brand-600 dark:text-brand-300">Live Data</p>
      </div>
    </motion.div>
  );
}
