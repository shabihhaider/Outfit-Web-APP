import { motion } from 'framer-motion'
import { resolveUrl } from '../../utils/resolveUrl.js'

const CAT_EMOJI = { top: '\u{1F455}', bottom: '\u{1F456}', outwear: '\u{1F9E5}', shoes: '\u{1F45F}', dress: '\u{1F457}', jumpsuit: '\u{1F938}' }

export default function OutfitItems({ items }) {
  if (!items || items.length === 0) return null

  return (
    <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
      {items.map((item, i) => {
        const imageUrl = resolveUrl(item.image_url)

        return (
          <motion.div 
            key={i}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="flex-shrink-0 group/item"
          >
            <div className="relative w-24 h-24 rounded-2xl overflow-hidden bg-white dark:bg-brand-800 border border-brand-100/60 dark:border-brand-700/40 shadow-sm group-hover/item:shadow-md transition-all duration-300 group-hover/item:-translate-y-1">
              {/* Subtle overlay gradient */}
              <div className="absolute inset-0 bg-gradient-to-t from-brand-900/10 to-transparent opacity-0 group-hover/item:opacity-100 transition-opacity" />
              
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt={item.category}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-3xl opacity-40 grayscale">
                  {CAT_EMOJI[item.category] || '\u{1F454}'}
                </div>
              )}
            </div>
            
            <div className="mt-2 flex flex-col items-center">
              <span className="text-[9px] font-bold uppercase tracking-widest text-brand-400 dark:text-brand-500 mb-0.5">
                {item.category}
              </span>
              {item.color_name && (
                <span className="text-[8px] text-brand-300 dark:text-brand-600 font-mono italic">
                  {item.color_name}
                </span>
              )}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
