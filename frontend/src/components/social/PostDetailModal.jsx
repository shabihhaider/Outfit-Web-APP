import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiHeart, FiRefreshCw, FiBookmark, FiUserPlus, FiUserCheck, FiUser } from 'react-icons/fi'
import { getPost, toggleLike, toggleBookmark, followUser, unfollowUser } from '../../api/social.js'
import { useAuth } from '../../context/AuthContext.jsx'
import VibeTagPill from './VibeTagPill.jsx'
import OutfitTryOnModal from '../tryon/OutfitTryOnModal.jsx'
import { resolveUrl } from '../../utils/resolveUrl.js'

export default function PostDetailModal({ post, open, onClose, onRemixClick, onVibeClick }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()

  // Fetch full post data (includes items)
  const { data: fullPost } = useQuery({
    queryKey: ['post', post?.id],
    queryFn: () => getPost(post.id),
    enabled: !!post?.id && open,
    staleTime: 30 * 1000,
  })

  const p = fullPost ?? post

  const [liked,       setLiked]      = useState(post?.is_liked ?? false)
  const [likeCount,   setLikeCount]  = useState(post?.like_count ?? 0)
  const [bookmarked,  setBookmarked] = useState(post?.is_bookmarked ?? false)
  const [following,   setFollowing]  = useState(post?.is_following_author ?? false)
  const [imgError,    setImgError]   = useState(false)

  // Sync like/save/follow state from fresh API data when fullPost resolves
  useEffect(() => {
    if (fullPost) {
      setLiked(fullPost.is_liked ?? false)
      setLikeCount(fullPost.like_count ?? 0)
      setBookmarked(fullPost.is_bookmarked ?? false)
      setFollowing(fullPost.is_following_author ?? false)
    }
  }, [fullPost])
  const [tryOnOpen,   setTryOnOpen]  = useState(false)

  const isOwn = user?.id === p?.user_id
  const previewUrl = p?.preview_url ? resolveUrl(p.preview_url) : null
  const username = p?.user?.username || `user_${p?.user_id}`

  // Collect item images — from full post items OR from outfit.item_images
  const itemImages = fullPost?.items?.map(i => i.image_url).filter(Boolean)
    ?? p?.outfit?.item_images
    ?? []

  const likeMutation = useMutation({
    mutationFn: () => toggleLike(p.id),
    onMutate:  () => { setLiked(v => !v); setLikeCount(v => liked ? v - 1 : v + 1) },
    onError:   () => { setLiked(v => !v); setLikeCount(v => liked ? v + 1 : v - 1) },
    onSuccess: (data) => { setLiked(data.liked); setLikeCount(data.like_count); qc.invalidateQueries({ queryKey: ['feed'] }) },
  })

  const bookmarkMutation = useMutation({
    mutationFn: () => toggleBookmark(p.id),
    onMutate:  () => setBookmarked(v => !v),
    onError:   () => setBookmarked(v => !v),
    onSuccess: (data) => { setBookmarked(data.bookmarked); qc.invalidateQueries({ queryKey: ['feed', 'saved'] }) },
  })

  const followMutation = useMutation({
    mutationFn: () => following ? unfollowUser(p.user_id) : followUser(p.user_id),
    onMutate:  () => setFollowing(v => !v),
    onError:   () => setFollowing(v => !v),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['feed'] }) },
  })

  if (!open || !post) return null

  return (
    <>
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-md"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ type: 'spring', damping: 26, stiffness: 320 }}
            className="relative z-10 w-full max-w-3xl bg-white dark:bg-brand-900 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col sm:flex-row"
          >
            {/* Left — image mosaic (always square) */}
            <div className="w-full sm:w-[45%] aspect-square flex-shrink-0 overflow-hidden bg-brand-100 dark:bg-brand-800">
              {previewUrl && !imgError ? (
                <img src={previewUrl} alt="Outfit" className="w-full h-full object-cover" onError={() => setImgError(true)} />
              ) : itemImages.length > 0 ? (
                <ModalMosaic images={itemImages} occasion={p?.outfit?.occasion} score={p?.outfit?.final_score} />
              ) : (
                <ModalPlaceholder outfit={p?.outfit} />
              )}
            </div>

            {/* Right — details */}
            <div className="flex flex-col flex-1 overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-brand-100 dark:border-brand-800">
                <div className="flex items-center gap-2 min-w-0">
                  <button
                    onClick={() => { onClose(); navigate(`/u/${username}`) }}
                    className="flex items-center gap-2 text-sm font-semibold text-brand-800 dark:text-brand-200 hover:text-accent-600 transition-colors min-w-0"
                  >
                    <div className="w-8 h-8 rounded-full overflow-hidden bg-brand-200 dark:bg-brand-700 flex-shrink-0 flex items-center justify-center text-xs font-bold text-brand-600 dark:text-brand-300">
                      {p?.user?.avatar_url ? (
                        <img src={resolveUrl(p.user.avatar_url)} alt="" className="w-full h-full object-cover" />
                      ) : (
                        (p?.user?.name?.[0] || username[0]).toUpperCase()
                      )}
                    </div>
                    <span className="truncate">@{username}</span>
                  </button>

                  {/* Follow button */}
                  {!isOwn && (
                    <button
                      onClick={() => followMutation.mutate()}
                      disabled={followMutation.isPending}
                      className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-all ${
                        following
                          ? 'bg-brand-100 dark:bg-brand-800 text-brand-500 dark:text-brand-400 hover:bg-red-50 hover:text-red-500'
                          : 'bg-accent-500 text-white hover:bg-accent-600'
                      } disabled:opacity-50`}
                    >
                      {following ? <><FiUserCheck size={11} /> Following</> : <><FiUserPlus size={11} /> Follow</>}
                    </button>
                  )}
                </div>

                <button
                  onClick={onClose}
                  className="p-2 rounded-lg text-brand-400 hover:text-brand-600 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors flex-shrink-0"
                >
                  <FiX size={18} />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Caption */}
                {p?.caption && (
                  <p className="text-sm text-brand-700 dark:text-brand-300 leading-relaxed">{p.caption}</p>
                )}

                {/* Outfit info */}
                {p?.outfit && (
                  <div className="flex items-center gap-3 text-xs text-brand-400">
                    <span className="capitalize font-medium">{p.outfit.occasion}</span>
                    {p.outfit.final_score != null && (
                      <span>{Math.round(p.outfit.final_score * 100)}% match</span>
                    )}
                    <span>{p.outfit.item_count} items</span>
                  </div>
                )}

                {/* Item thumbnails row (from full post) */}
                {fullPost?.items?.length > 0 && (
                  <div className="grid grid-cols-4 gap-2">
                    {fullPost.items.map((item, i) => (
                      <div key={i} className="aspect-square rounded-lg overflow-hidden bg-brand-100 dark:bg-brand-800 border border-brand-200 dark:border-brand-700">
                        {item.image_url ? (
                          <img src={resolveUrl(item.image_url)} alt={item.category} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-xl opacity-30">
                            <span className="select-none">?</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Vibe tags */}
                {p?.vibes?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {p.vibes.map(v => (
                      <VibeTagPill
                        key={v.slug}
                        slug={v.slug}
                        label={v.label}
                        size="xs"
                        onClick={() => onVibeClick?.(v.slug)}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Actions footer */}
              <div className="p-4 border-t border-brand-100 dark:border-brand-800 flex items-center gap-2">
                <button
                  onClick={() => likeMutation.mutate()}
                  disabled={isOwn}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    liked
                      ? 'text-red-500 bg-red-50 dark:bg-red-900/20'
                      : 'text-brand-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10'
                  } disabled:opacity-40 disabled:cursor-default`}
                >
                  <FiHeart size={15} className={liked ? 'fill-red-500' : ''} />
                  <span>{likeCount}</span>
                </button>

                {fullPost?.items?.length > 0 && (
                  <button
                    onClick={() => setTryOnOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-brand-500 hover:text-accent-600 hover:bg-accent-50 dark:hover:bg-accent-900/15 transition-all"
                  >
                    <FiUser size={15} />
                    <span>Try On</span>
                  </button>
                )}

                {!isOwn && (
                  <button
                    onClick={() => onRemixClick?.(p)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-brand-500 hover:text-accent-600 hover:bg-accent-50 dark:hover:bg-accent-900/15 transition-all"
                  >
                    <FiRefreshCw size={15} />
                    <span>Remix</span>
                  </button>
                )}

                {!isOwn && (
                  <button
                    onClick={() => bookmarkMutation.mutate()}
                    className={`ml-auto flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                      bookmarked
                        ? 'text-accent-600 bg-accent-50 dark:bg-accent-900/20'
                        : 'text-brand-400 hover:text-accent-600 hover:bg-accent-50 dark:hover:bg-accent-900/10'
                    }`}
                  >
                    <FiBookmark size={15} className={bookmarked ? 'fill-accent-600' : ''} />
                    {bookmarked ? 'Saved' : 'Save'}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>

    <OutfitTryOnModal
      open={tryOnOpen}
      onClose={() => setTryOnOpen(false)}
      items={fullPost?.items ?? []}
      occasion={p?.outfit?.occasion}
    />
  </>
  )
}

/* ─── Modal Left-Panel Mosaic ───────────────────────────────────────── */

function ModalMosaic({ images, occasion, score }) {
  const urls = images.slice(0, 4)
  const n = urls.length

  const gridClass =
    n === 1 ? 'grid-cols-1 grid-rows-1' :
    n === 2 ? 'grid-cols-2 grid-rows-1' :
              'grid-cols-2 grid-rows-2'

  return (
    <div className="relative w-full h-full">
      <div className={`w-full h-full grid gap-[2px] ${gridClass}`}>
        {urls.map((url, i) => (
          <div
            key={i}
            className={`relative overflow-hidden bg-brand-200/60 dark:bg-brand-700/50 ${
              n === 3 && i === 0 ? 'row-span-2' : ''
            }`}
          >
            <img
              src={resolveUrl(url)}
              alt=""
              className="absolute inset-0 w-full h-full object-cover"
              onError={e => { e.currentTarget.style.display = 'none' }}
            />
          </div>
        ))}
      </div>

      {/* Gradient overlay */}
      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 via-black/25 to-transparent pt-14 pb-3 px-4 flex items-end justify-between pointer-events-none">
        {occasion && (
          <span className="text-xs font-bold uppercase tracking-wider text-white/90 bg-white/15 backdrop-blur-sm px-2.5 py-1 rounded-full">
            {occasion}
          </span>
        )}
        {score != null && (
          <span className="text-xs font-semibold text-white/75">
            {Math.round(score * 100)}%
          </span>
        )}
      </div>
    </div>
  )
}

/* ─── Fallback Placeholder ──────────────────────────────────────────── */

const OCC_STYLES = {
  casual:  { grad: 'from-sky-500/30 via-blue-400/15 to-indigo-400/10',       accent: 'text-sky-400',     icon: '👕' },
  formal:  { grad: 'from-violet-500/30 via-purple-400/15 to-fuchsia-400/10', accent: 'text-violet-400',  icon: '👔' },
  wedding: { grad: 'from-rose-500/30 via-pink-400/15 to-red-400/10',         accent: 'text-rose-400',    icon: '🌸' },
}

function ModalPlaceholder({ outfit }) {
  const occ   = outfit?.occasion?.toLowerCase() || 'casual'
  const style = OCC_STYLES[occ] || OCC_STYLES.casual
  const score = outfit?.final_score != null ? Math.round(outfit.final_score * 100) : null
  const count = outfit?.item_count ?? null
  return (
    <div className={`w-full h-full flex flex-col items-center justify-center gap-4 bg-gradient-to-br ${style.grad}`}>
      <span className="text-7xl drop-shadow select-none">{style.icon}</span>
      <span className={`text-sm font-bold uppercase tracking-widest ${style.accent}`}>{occ}</span>
      <div className="flex items-center gap-4 text-xs text-brand-400 dark:text-brand-500">
        {score != null && <span>{score}% match</span>}
        {count != null && <span>{count} items</span>}
      </div>
    </div>
  )
}
