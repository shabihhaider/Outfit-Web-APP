import { useState, useRef, useCallback } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiUsers, FiCompass, FiBookmark } from 'react-icons/fi'
import { getFeed, getBookmarks, getTrendingVibes } from '../api/social.js'
import { useQuery } from '@tanstack/react-query'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import FeedCard from '../components/social/FeedCard.jsx'
import RemixResultModal from '../components/social/RemixResultModal.jsx'
import PostDetailModal from '../components/social/PostDetailModal.jsx'
import VibeTagPill from '../components/social/VibeTagPill.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'

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
  const observerRef = useRef(null)

  // Trending vibes banner
  const { data: trendingVibesData } = useQuery({
    queryKey: ['trending-vibes'],
    queryFn:  getTrendingVibes,
    staleTime: 5 * 60 * 1000,
  })
  const trendingVibes = trendingVibesData ?? []

  // Infinite feed query
  const {
    data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError,
  } = useInfiniteQuery({
    queryKey: ['feed', tab, vibeFilter],
    queryFn: ({ pageParam: cursor }) => {
      if (tab === 'saved') {
        return getBookmarks({ cursor, limit: 20 })
      }
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
      if (entries[0].isIntersecting && hasNextPage) {
        fetchNextPage()
      }
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

        {/* Trending vibes banner */}
        {trendingVibes.length > 0 && tab === 'discover' && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <p className="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-2">
              🔥 Trending now
            </p>
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
              {/* "All" pill */}
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
                  {v.emoji || ''} {v.label}
                  {v.post_count > 0 && <span className="ml-1 opacity-60">{v.post_count}</span>}
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
              onClick={() => { setTab(t.key); setVibeFilter(null) }}
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
                  <div className="flex gap-1">
                    <div className="skeleton h-5 w-12 rounded-full" />
                    <div className="skeleton h-5 w-14 rounded-full" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {isError && (
          <EmptyState
            icon="⚠️"
            title="Feed unavailable"
            description="Could not load posts. Please try again."
          />
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
                ? 'Discover users in the Discover tab and follow the ones whose style resonates with you.'
                : tab === 'saved'
                ? 'Bookmark posts from the feed to save inspiration for later.'
                : vibeFilter
                ? `No posts tagged with this vibe yet. Be the first!`
                : 'Be the first to publish an outfit from your Saved collection.'
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
