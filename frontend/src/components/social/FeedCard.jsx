import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiHeart, FiRefreshCw, FiBookmark, FiMoreHorizontal } from 'react-icons/fi'
import { toggleLike, toggleBookmark, deletePost } from '../../api/social.js'
import VibeTagPill from './VibeTagPill.jsx'
import ConfirmDialog from '../ui/ConfirmDialog.jsx'
import { useAuth } from '../../context/AuthContext.jsx'

const BASE = import.meta.env.VITE_API_URL || ''

export default function FeedCard({ post, onRemixClick, onVibeClick, onPostClick }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc       = useQueryClient()

  const [liked,      setLiked]      = useState(post.is_liked ?? false)
  const [likeCount,  setLikeCount]  = useState(post.like_count ?? 0)
  const [bookmarked, setBookmarked] = useState(post.is_bookmarked ?? false)
  const [menuOpen,   setMenuOpen]   = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const [imageError, setImageError] = useState(false)

  const isOwn = user?.id === post.user_id

  const likeMutation = useMutation({
    mutationFn: () => toggleLike(post.id),
    onMutate: () => {
      setLiked(v => !v)
      setLikeCount(v => liked ? v - 1 : v + 1)
    },
    onError: () => {
      setLiked(v => !v)
      setLikeCount(v => liked ? v + 1 : v - 1)
    },
    onSuccess: (data) => {
      setLiked(data.liked)
      setLikeCount(data.like_count)
      qc.invalidateQueries({ queryKey: ['feed'] })
    },
  })

  const bookmarkMutation = useMutation({
    mutationFn: () => toggleBookmark(post.id),
    onMutate: () => setBookmarked(v => !v),
    onError:  () => setBookmarked(v => !v),
    onSuccess: (data) => {
      setBookmarked(data.bookmarked)
      qc.invalidateQueries({ queryKey: ['feed', 'saved'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deletePost(post.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feed'] })
      qc.invalidateQueries({ queryKey: ['social-profile'] })
    },
  })

  const previewUrl  = post.preview_url ? `${BASE}${post.preview_url}` : null
  const itemImages  = post.outfit?.item_images ?? []
  const username    = post.user?.username || `user_${post.user_id}`
  const timeAgo     = _timeAgo(post.created_at)

  return (
    <>
      <motion.div
        layout
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="card overflow-hidden group"
      >
        {/* Image area — cascading fallback: preview → item mosaic → occasion card */}
        <div
          className="relative aspect-square bg-brand-100 dark:bg-brand-800 overflow-hidden cursor-pointer"
          onClick={() => onPostClick?.(post)}
        >
          {previewUrl && !imageError ? (
            <img
              src={previewUrl}
              alt="Outfit preview"
              loading="lazy"
              decoding="async"
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              onError={() => setImageError(true)}
            />
          ) : itemImages.length > 0 ? (
            <ItemMosaic
              images={itemImages}
              occasion={post.outfit?.occasion}
              score={post.outfit?.final_score}
            />
          ) : (
            <OccasionCard outfit={post.outfit} />
          )}

          {/* Remix source badge */}
          {post.remix_source_post_id && (
            <div className="absolute top-2 left-2 bg-black/50 text-white text-[10px] px-2 py-0.5 rounded-full backdrop-blur-sm">
              Remixed
            </div>
          )}
        </div>

        {/* Card body */}
        <div className="p-3">
          {/* Author + time */}
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => navigate(`/u/${username}`)}
              className="flex items-center gap-1.5 text-sm font-semibold text-brand-800 dark:text-brand-200 hover:text-accent-600 transition-colors"
            >
              <div className="w-6 h-6 rounded-full overflow-hidden bg-brand-200 dark:bg-brand-700 flex-shrink-0 flex items-center justify-center text-[10px] font-bold text-brand-600 dark:text-brand-300">
                {post.user?.avatar_url ? (
                  <img src={`${BASE}${post.user.avatar_url}`} alt="" className="w-full h-full object-cover" />
                ) : (
                  (post.user?.name?.[0] || username[0]).toUpperCase()
                )}
              </div>
              @{username}
            </button>
            <div className="flex items-center gap-1">
              <span className="text-[11px] text-brand-400">{timeAgo}</span>
              {isOwn && (
                <div className="relative">
                  <button
                    onClick={() => setMenuOpen(v => !v)}
                    className="p-1 rounded text-brand-400 hover:text-brand-600 transition-colors"
                  >
                    <FiMoreHorizontal size={14} />
                  </button>
                  {menuOpen && (
                    <div className="absolute right-0 top-6 z-20 bg-white dark:bg-brand-900 rounded-lg shadow-lg border border-brand-100 dark:border-brand-800 min-w-[110px]">
                      <button
                        onClick={() => { setMenuOpen(false); setConfirmDel(true) }}
                        className="w-full text-left px-3 py-2 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                      >
                        Delete post
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Caption */}
          {post.caption && (
            <p className="text-sm text-brand-700 dark:text-brand-300 mb-2 leading-snug line-clamp-2">
              {post.caption}
            </p>
          )}

          {/* Vibe tags */}
          {post.vibes?.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {post.vibes.map(v => (
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

          {/* Actions */}
          <div className="flex items-center gap-1 pt-2 border-t border-brand-100/60 dark:border-brand-800/40">
            {/* Like */}
            <button
              onClick={() => likeMutation.mutate()}
              disabled={isOwn}
              className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                liked
                  ? 'text-red-500 bg-red-50 dark:bg-red-900/20'
                  : 'text-brand-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10'
              } disabled:opacity-40 disabled:cursor-default`}
            >
              <FiHeart size={13} className={liked ? 'fill-red-500' : ''} />
              <span>{likeCount}</span>
            </button>

            {/* Remix */}
            {!isOwn && (
              <button
                onClick={() => onRemixClick?.(post)}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium text-brand-500 hover:text-accent-600 hover:bg-accent-50 dark:hover:bg-accent-900/15 transition-all"
              >
                <FiRefreshCw size={13} />
                <span>{post.remix_count > 0 ? post.remix_count : 'Remix'}</span>
              </button>
            )}

            {/* Bookmark */}
            {!isOwn && (
              <button
                onClick={() => bookmarkMutation.mutate()}
                className={`ml-auto flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  bookmarked
                    ? 'text-accent-600 bg-accent-50 dark:bg-accent-900/20'
                    : 'text-brand-400 hover:text-accent-600 hover:bg-accent-50 dark:hover:bg-accent-900/10'
                }`}
              >
                <FiBookmark size={13} className={bookmarked ? 'fill-accent-600' : ''} />
              </button>
            )}
          </div>
        </div>
      </motion.div>

      <ConfirmDialog
        open={confirmDel}
        title="Delete Post"
        message="Remove this post from the social feed? This cannot be undone."
        danger
        onConfirm={() => { setConfirmDel(false); deleteMutation.mutate() }}
        onCancel={() => setConfirmDel(false)}
      />
    </>
  )
}

/* ─── Item Image Mosaic ─────────────────────────────────────────────── */
/* Instagram collection-style layout: adapts to 1, 2, 3, or 4 items.
   Always fills the parent square. Gradient overlay with occasion badge. */

function ItemMosaic({ images, occasion, score }) {
  const urls = images.slice(0, 4)
  const n = urls.length

  // Choose grid layout based on item count
  const gridClass =
    n === 1 ? 'grid-cols-1 grid-rows-1' :
    n === 2 ? 'grid-cols-2 grid-rows-1' :
              'grid-cols-2 grid-rows-2'

  return (
    <div className="relative w-full h-full">
      {/* Image grid */}
      <div className={`w-full h-full grid gap-[2px] ${gridClass}`}>
        {urls.map((url, i) => (
          <div
            key={i}
            className={`relative overflow-hidden bg-brand-200/60 dark:bg-brand-700/50 ${
              n === 3 && i === 0 ? 'row-span-2' : ''
            }`}
          >
            <img
              src={`${BASE}${url}`}
              alt=""
              loading="lazy"
              decoding="async"
              className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              onError={e => {
                e.currentTarget.style.display = 'none'
              }}
            />
          </div>
        ))}
      </div>

      {/* Gradient overlay with occasion + score — always present */}
      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 via-black/25 to-transparent pt-12 pb-2.5 px-3 flex items-end justify-between pointer-events-none">
        {occasion && (
          <span className="text-[10px] font-bold uppercase tracking-wider text-white/90 bg-white/15 backdrop-blur-sm px-2 py-0.5 rounded-full">
            {occasion}
          </span>
        )}
        {score != null && (
          <span className="text-[10px] font-semibold text-white/75">
            {Math.round(score * 100)}% match
          </span>
        )}
      </div>
    </div>
  )
}

/* ─── Occasion-Only Placeholder ─────────────────────────────────────── */
/* Last resort when no preview and no item images exist at all. */

const OCC_STYLES = {
  casual:  { grad: 'from-sky-500/30 via-blue-400/15 to-indigo-400/10',   accent: 'text-sky-400',     icon: '👕' },
  formal:  { grad: 'from-violet-500/30 via-purple-400/15 to-fuchsia-400/10', accent: 'text-violet-400', icon: '👔' },
  wedding: { grad: 'from-rose-500/30 via-pink-400/15 to-red-400/10',     accent: 'text-rose-400',    icon: '🌸' },
}

function OccasionCard({ outfit }) {
  const occ   = outfit?.occasion?.toLowerCase() || 'casual'
  const style = OCC_STYLES[occ] || OCC_STYLES.casual
  const score = outfit?.final_score != null ? Math.round(outfit.final_score * 100) : null
  const count = outfit?.item_count ?? null

  return (
    <div className={`w-full h-full flex flex-col items-center justify-center gap-3 bg-gradient-to-br ${style.grad}`}>
      <span className="text-5xl drop-shadow-sm select-none">{style.icon}</span>
      <span className={`text-[11px] font-bold uppercase tracking-widest ${style.accent}`}>
        {occ}
      </span>
      <div className="flex items-center gap-3 text-[10px] text-brand-400 dark:text-brand-500">
        {score != null && <span>{score}% match</span>}
        {count != null && <span>{count} items</span>}
      </div>
    </div>
  )
}

/* ─── Helpers ───────────────────────────────────────────────────────── */

function _timeAgo(isoString) {
  if (!isoString) return ''
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000
  if (diff < 60)        return `${Math.floor(diff)}s`
  if (diff < 3600)      return `${Math.floor(diff / 60)}m`
  if (diff < 86400)     return `${Math.floor(diff / 3600)}h`
  if (diff < 2592000)   return `${Math.floor(diff / 86400)}d`
  return new Date(isoString).toLocaleDateString()
}
