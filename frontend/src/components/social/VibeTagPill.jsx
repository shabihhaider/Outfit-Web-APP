const VIBE_COLORS = {
  'streetwear':             'bg-zinc-800 text-zinc-100',
  'minimalist':             'bg-stone-100 text-stone-700 border border-stone-300',
  'old-money':              'bg-amber-50 text-amber-900 border border-amber-200',
  'cottagecore':            'bg-green-100 text-green-800',
  'dark-academia':          'bg-neutral-800 text-neutral-200',
  'y2k':                    'bg-pink-200 text-pink-900',
  'boho':                   'bg-orange-100 text-orange-800',
  'grunge':                 'bg-gray-700 text-gray-200',
  'preppy':                 'bg-blue-100 text-blue-800',
  'athleisure':             'bg-sky-100 text-sky-800',
  'party-glam':             'bg-purple-200 text-purple-900',
  'quiet-luxury':           'bg-slate-100 text-slate-700 border border-slate-300',
  'coastal':                'bg-cyan-100 text-cyan-800',
  'balletcore':             'bg-rose-100 text-rose-800',
  'techwear':               'bg-gray-900 text-gray-300',
  'gorpcore':               'bg-lime-100 text-lime-800',
  'avant-garde':            'bg-fuchsia-100 text-fuchsia-900',
  'mob-wife':               'bg-red-900 text-red-100',
  'business-casual':        'bg-blue-50 text-blue-900 border border-blue-200',
  'smart-casual':           'bg-indigo-50 text-indigo-800',
  'desi-casual':            'bg-emerald-100 text-emerald-900',
  'desi-formal':            'bg-red-100 text-red-900',
  'fusion-east-west':       'bg-violet-100 text-violet-900',
  'lawn-chic':              'bg-lime-200 text-lime-900',
  'bridal-south-asian':     'bg-red-200 text-red-900',
  'mehndi-festive':         'bg-orange-200 text-orange-900',
  'modest-fashion':         'bg-teal-100 text-teal-800',
  'south-asian-streetwear': 'bg-yellow-100 text-yellow-900',
  'mughal-luxe':            'bg-amber-200 text-amber-900',
  'peshawari-traditional':  'bg-brown-100 text-stone-800 border border-stone-300',
}

const DEFAULT_COLOR = 'bg-brand-100 text-brand-700 dark:bg-brand-800 dark:text-brand-300'

export default function VibeTagPill({ slug, label, size = 'sm', onClick }) {
  const colorClass = VIBE_COLORS[slug] || DEFAULT_COLOR
  const sizeClass  = size === 'xs' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center rounded-full font-medium whitespace-nowrap transition-opacity ${colorClass} ${sizeClass} ${onClick ? 'hover:opacity-80 cursor-pointer' : 'cursor-default'}`}
    >
      {label}
    </button>
  )
}
