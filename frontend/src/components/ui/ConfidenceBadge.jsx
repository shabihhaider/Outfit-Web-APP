import { confidenceColor } from '../../utils/formatters.js'

export default function ConfidenceBadge({ level }) {
  const getGlowColor = (lvl) => {
    switch(lvl?.toLowerCase()) {
      case 'high': return 'shadow-[0_0_12px_rgba(16,185,129,0.2)]'
      case 'medium': return 'shadow-[0_0_12px_rgba(245,158,11,0.2)]'
      case 'low': return 'shadow-[0_0_12px_rgba(239,68,68,0.2)]'
      default: return ''
    }
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-[0.15em] border ${confidenceColor(level)} ${getGlowColor(level)} backdrop-blur-sm transition-all duration-500`}>
      <span className="mr-1.5 w-1 h-1 rounded-full bg-current animate-pulse" />
      {level || 'Analysis Pending'}
    </span>
  )
}
