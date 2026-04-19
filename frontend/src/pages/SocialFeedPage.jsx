import { useState, useRef, useCallback, useEffect } from 'react'
import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FiUsers, FiCompass, FiBookmark, FiSearch, FiUserPlus, FiUserCheck } from 'react-icons/fi'
import { getFeed, getBookmarks, getTrendingVibes, searchUsers, followUser, unfollowUser } from '../api/social.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import FeedCard from '../components/social/FeedCard.jsx'
import RemixResultModal from '../components/social/RemixResultModal.jsx'
import PostDetailModal from '../components/social/PostDetailModal.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import { resolveUrl } from '../utils/resolveUrl.js'

const TABS = [
  { key: 'discover',  label: 'Discover', Icon: FiCompass },
  { key: 'following', label: 'Following', Icon: FiUsers },
  { key: 'saved',     label: 'Saved',    Icon: FiBookmark },
]

export default function SocialFeedPage() {
  const [tab,          setTab]          = useState('discover')
  const [vibeFilter,   setVibeFilter]   = useState(null)
  const [remixTarget,  setRemixTarget]  = useState(null)
  const [detailPost,   setDetailPost]   = useState(null)
  const [searchQ,      setSearchQ]      = useState('')
  const [debouncedQ,   setDebouncedQ]   = useState('')
  const observerRef = useRef(null)
  const navigate = useNavigate()
  const qc = useQueryClient()

  // Debounce search query 300ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(searchQ.trim()), 300)
    return () => clearTimeout(t)
  }, [searchQ])

  // Trending vibes banner
  const { data: trendingVibesData } = useQuery({
    queryKey: ['trending-vibes'],
    queryFn:  getTrendingVibes,
    staleTime: 5 * 60 * 1000,
  })
  const trendingVibes = trendingVibesData ?? []

  // User search query — only fires when q >= 2 chars
  const { data: searchData, isFetching: isSearching } = useQuery({
    queryKey: ['user-search', debouncedQ],
    queryFn:  () => searchUsers(debouncedQ),
    enabled:  debouncedQ.length >= 2 && tab === 'discover',
    staleTime: 30 * 1000,
  })
  const searchResults = searchData?.users ?? []
  const showSearch = tab === 'discover' && debouncedQ.length >= 2

  // Infinite feed query
  const {
    data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError,
  } = useInfiniteQuery({
    queryKey: ['feed', tab, vibeFilter],
    queryFn: ({ pageParam: cursor }) => {
      if (tab === 'saved') return getBookmarks({ cursor, limit: 20 })
      return getFeed({ tab, cursor, limit: 20, ...(vibeFilter ? { vibe: vibeFilter } : {}) })
    },
    getNextPageParam: (lastPage) => lastPage.pagination?.next_cursor ?? undefined,
    initialPageParam: undefined,
  })

  // Intersection observer for infinite scroll
  const lastCardRef = useCallback(node => {
    if (isFetchingNextPage) return
    if (observerRef.current) observerRef.current.disconnect()
    observerRef.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasNextPage) fetchNextPage()
    }, { threshold: 0.1 })
    if (node) observerRef.current.observe(node)
  }, [isFetchingNextPage, hasNextPage, fetchNextPage])

  const allPosts = data?.pages.flatMap(p => p.posts ?? []) ?? []

  return (
    <>
      <PageWrapper>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <p className="label-xs mb-1">Community</p>
          <h1 className="font-display text-4xl sm:text-5xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
            Atelier Social
          </h1>
        </motion.div>

        {/* Search bar — Discover tab only */}
        {tab === 'discover' && (
          <div className="relative mb-6">
            <FiSearch size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-500" />
            <input
              type="text"
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
              placeholder="Search people by username or name…"
              className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-brand-200/60 dark:border-brand-700/40 bg-white dark:bg-brand-900 text-sm text-brand-800 dark:text-brand-200 placeholder:text-brand-500 dark:placeholder:text-brand-600 focus:outline-none focus:ring-2 focus:ring-accent-400 transition-all"
            />
          </div>
        )}

        {/* Search results */}
        <AnimatePresence>
          {showSearch && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="card p-3 mb-6 space-y-1"
            >
              {isSearching && (
                <div className="py-4 flex justify-center">
                  <div className="w-5 h-5 border-2 border-brand-200 border-t-accent-500 rounded-full animate-spin" />
                </div>
              )}
              {!isSearching && searchResults.length === 0 && (
                <p className="text-sm text-brand-500 dark:text-brand-400 text-center py-3">
                  No users found for &ldquo;{debouncedQ}&rdquo;
                </p>
              )}
              {!isSearching && searchResults.map(u => (
                <UserSearchRow
                  key={u.id}
                  user={u}
                  onNavigate={() => navigate(`/u/${u.username}`)}
                  onFollowChange={() => qc.invalidateQueries({ queryKey: ['user-search', debouncedQ] })}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Trending vibes banner */}
        {trendingVibes.length > 0 && tab === 'discover' && !showSearch && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <p className="text-xs font-semibold text-brand-500 uppercase tracking-widest mb-2">
              🔥 Trending this week
            </p>
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
              <button
                onClick={() => setVibeFilter(null)}
                className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-full font-medium border transition-all ${
                  vibeFilter === null
                    ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900'
                    : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400'
                }`}
              >
                All
              </button>
              {trendingVibes.map(v => (
                <button
                  key={v.slug}
                  onClick={() => setVibeFilter(vibeFilter === v.slug ? null : v.slug)}
                  className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-full font-medium border transition-all ${
                    vibeFilter === v.slug
                      ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900'
                      : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400'
                  }`}
                >
                  {v.label}
                  {v.score > 0 && <span className="ml-1 opacity-50 font-mono">{v.score}</span>}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 bg-brand-100/60 dark:bg-brand-900/30 rounded-xl p-1 mb-8 w-full sm:w-fit">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => { setTab(t.key); setVibeFilter(null); setSearchQ('') }}
              className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t.key
                  ? 'bg-white dark:bg-brand-800 text-brand-900 dark:text-brand-100 shadow-sm'
                  : 'text-brand-500 hover:text-brand-700 dark:hover:text-brand-300'
              }`}
            >
              <t.Icon size={14} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Feed grid */}
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card overflow-hidden">
                <div className="skeleton aspect-square" />
                <div className="p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="skeleton w-6 h-6 rounded-full" />
                    <div className="skeleton h-3 w-20 rounded" />
                  </div>
                  <div className="skeleton h-3 w-full rounded" />
                </div>
              </div>
            ))}
          </div>
        )}

        {isError && (
          <EmptyState icon="⚠️" title="Feed unavailable" description="Could not load posts. Please try again." />
        )}

        {!isLoading && !isError && allPosts.length === 0 && (
          <EmptyState
            icon={tab === 'following' ? '👥' : tab === 'saved' ? '🔖' : '✨'}
            title={
              tab === 'following' ? 'Follow stylists to see their posts'
              : tab === 'saved'   ? 'No saved posts yet'
              : 'No posts here yet'
            }
            description={
              tab === 'following'
                ? 'Use the search bar on Discover to find people and follow the ones whose style resonates with you.'
                : tab === 'saved'
                ? 'Bookmark posts from the feed to save inspiration for later.'
                : vibeFilter
                ? 'No posts tagged with this vibe yet. Be the first!'
                : 'Be the first to share an outfit with the community!'
            }
            action={
              tab === 'discover' && !vibeFilter
                ? { label: 'Share an outfit →', onClick: () => navigate('/saved') }
                : undefined
            }
          />
        )}

        {allPosts.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {allPosts.map((post, idx) => {
              const isLast = idx === allPosts.length - 1
              return (
                <div key={post.id} ref={isLast ? lastCardRef : undefined}>
                  <FeedCard
                    post={post}
                    onRemixClick={(p) => setRemixTarget(p)}
                    onVibeClick={(slug) => { setTab('discover'); setVibeFilter(slug) }}
                    onPostClick={(p) => setDetailPost(p)}
                  />
                </div>
              )
            })}
          </div>
        )}

        {isFetchingNextPage && (
          <div className="py-8 flex justify-center">
            <div className="w-6 h-6 border-2 border-brand-200 border-t-accent-500 rounded-full animate-spin" />
          </div>
        )}
      </PageWrapper>

      <RemixResultModal
        open={!!remixTarget}
        onClose={() => setRemixTarget(null)}
        post={remixTarget}
      />

      <PostDetailModal
        post={detailPost}
        open={!!detailPost}
        onClose={() => setDetailPost(null)}
        onRemixClick={(p) => { setDetailPost(null); setRemixTarget(p) }}
        onVibeClick={(slug) => { setDetailPost(null); setTab('discover'); setVibeFilter(slug) }}
      />
    </>
  )
}

function UserSearchRow({ user, onNavigate, onFollowChange }) {
  const [following, setFollowing] = useState(user.is_following)

  const followMutation = useMutation({
    mutationFn: () => following ? unfollowUser(user.id) : followUser(user.id),
    onSuccess: () => { setFollowing(v => !v); onFollowChange() },
  })

  return (
    <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-brand-50/60 dark:hover:bg-brand-800/30 transition-colors">
      <button onClick={onNavigate} className="flex items-center gap-3 flex-1 min-w-0 text-left">
        <div className="w-9 h-9 rounded-full overflow-hidden bg-brand-200 dark:bg-brand-700 flex-shrink-0">
          {user.avatar_url ? (
            <img src={resolveUrl(user.avatar_url)} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xs font-bold text-brand-600 dark:text-brand-300">
              {(user.name?.[0] || user.username?.[0] || '?').toUpperCase()}
            </div>
          )}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-brand-800 dark:text-brand-200 truncate">@{user.username}</p>
          <p className="text-xs text-brand-500 dark:text-brand-400 truncate">{user.name} · {user.follower_count} followers</p>
        </div>
      </button>
      <button
        onClick={() => followMutation.mutate()}
        disabled={followMutation.isPending}
        className={`flex-shrink-0 flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg transition-all ${
          following
            ? 'bg-brand-100 dark:bg-brand-800 text-brand-600 dark:text-brand-400'
            : 'btn-accent'
        }`}
      >
        {following ? <><FiUserCheck size={12} /> Following</> : <><FiUserPlus size={12} /> Follow</>}
      </button>
    </div>
  )
}
