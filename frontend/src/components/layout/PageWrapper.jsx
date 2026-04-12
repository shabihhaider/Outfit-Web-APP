import { motion } from 'framer-motion'

export default function PageWrapper({ children, className = '' }) {
  return (
    <motion.main
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={`max-w-6xl mx-auto px-4 sm:px-6 py-8 min-h-screen ${className}`}
    >
      {children}
    </motion.main>
  )
}
