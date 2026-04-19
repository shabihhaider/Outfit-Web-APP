import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiHeart, FiUserPlus, FiRefreshCw, FiBell } from 'react-icons/fi'
import { getNotifications, markAllRead } from '../../api/notifications.js'
import { resolveUrl } from '../../utils/resolveUrl.js'

const TYPE_ICON = {
  like:   <FiHeart size={13} className="text-red-400" />,
  follow: <FiUserPlus size={13} className="text-accent-700" />,
  remix:  <FiRefreshCw size={13} className="text-violet-400" />,
}

function timeAgo(isoStr) {
  if (!isoStr) return ''
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000
  if (diff < 60)  return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function NotificationsPanel({ open, onClose }) {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn:  () => getNotifications({ limit: 20 }),
    enabled:  open,
    staleTime: 30 * 1000,
  })

  const markRead = useMutation({
    mutationFn: markAllRead,
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['notifications-count'] }),
  })

  const notifications = data?.notifications ?? []
  const unread = data?.unread_count ?? 0

  // Mark read when panel opens
  if (open && unread > 0 && !markRead.isPending && !markRead.isSuccess) {
    markRead.mutate()
  }

  function handleClick(n) {
    onClose()
    if (n.post_id) navigate(`/feed`)
    else if (n.actor) navigate(`/u/${n.actor.username}`)
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ type: 'spring', damping: 28, stiffness: 380 }}
            className="fixed top-20 right-4 z-50 w-80 sm:w-96 bg-white dark:bg-brand-900 rounded-2xl shadow-2xl border border-brand-100/60 dark:border-brand-700/40 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-brand-100 dark:border-brand-800">
              <div className="flex items-center gap-2">
                <FiBell size={15} className="text-brand-500" />
                <span className="text-sm font-semibold text-brand-800 dark:text-brand-200">Notifications</span>
                {unread > 0 && (
                  <span className="bg-accent-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
                    {unread}
                  </span>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-brand-500 hover:text-brand-600 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors"
              >
                <FiX size={15} />
              </button>
            </div>

            {/* Body */}
            <div className="max-h-96 overflow-y-auto">
              {isLoading && (
                <div className="py-10 flex justify-center">
                  <div className="w-5 h-5 border-2 border-brand-200 border-t-accent-500 rounded-full animate-spin" />
                </div>
              )}

              {!isLoading && notifications.length === 0 && (
                <div className="py-12 text-center">
                  <FiBell size={28} className="mx-auto mb-3 text-brand-200 dark:text-brand-700" />
                  <p className="text-sm text-brand-500 dark:text-brand-400">No notifications yet</p>
                  <p className="text-xs text-brand-300 dark:text-brand-600 mt-1">
                    Likes, follows, and remixes will appear here
                  </p>
                </div>
              )}

              {!isLoading && notifications.map(n => (
                <button
                  key={n.id}
                  onClick={() => handleClick(n)}
                  className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-brand-50 dark:hover:bg-brand-800/40 ${
                    !n.read ? 'bg-accent-50/40 dark:bg-accent-900/10' : ''
                  }`}
                >
                  {/* Avatar */}
                  <div className="relative flex-shrink-0">
                    <div className="w-9 h-9 rounded-full overflow-hidden bg-brand-200 dark:bg-brand-700 flex items-center justify-center text-xs font-bold text-brand-600 dark:text-brand-300">
                      {n.actor?.avatar_url ? (
                        <img src={resolveUrl(n.actor.avatar_url)} alt="" className="w-full h-full object-cover" />
                      ) : (
                        (n.actor?.username?.[0] || '?').toUpperCase()
                      )}
                    </div>
                    {/* Type icon badge */}
                    <div className="absolute -bottom-0.5 -right-0.5 w-4.5 h-4.5 bg-white dark:bg-brand-900 rounded-full flex items-center justify-center border border-brand-100 dark:border-brand-700">
                      {TYPE_ICON[n.type] ?? <FiBell size={10} />}
                    </div>
                  </div>

                  {/* Text */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-brand-700 dark:text-brand-200 leading-snug">{n.message}</p>
                    <p className="text-xs text-brand-500 dark:text-brand-400 mt-0.5">{timeAgo(n.created_at)}</p>
                  </div>

                  {/* Unread dot */}
                  {!n.read && (
                    <div className="flex-shrink-0 w-2 h-2 rounded-full bg-accent-500 mt-1.5" />
                  )}
                </button>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
