import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiArrowLeft, FiRefreshCw } from 'react-icons/fi'
import { getPublicProfile, getCompatibility } from '../api/social.js'
import { useAuth } from '../context/AuthContext.jsx'
import { resolveUrl } from '../utils/resolveUrl.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import FeedCard from '../components/social/FeedCard.jsx'
import FollowButton from '../components/social/FollowButton.jsx'
import RemixResultModal from '../components/social/RemixResultModal.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'

export default function PublicProfilePage() {
  const { username }   = useParams()
  const { user: me }   = useAuth()
  const navigate       = useNavigate()
  const [remixTarget,  setRemixTarget] = useState(null)
  const [isFollowing,  setIsFollowing] = useState(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['social-profile', username],
    queryFn:  () => getPublicProfile(username),
    onSuccess: (d) => {
      if (isFollowing === null) setIsFollowing(d.is_following)
    },
  })

  const { data: compatData } = useQuery({
    queryKey: ['compatibility', username],
    queryFn:  () => getCompatibility(username),
    enabled:  !!data && data.user?.id !== me?.id,
  })

  if (isLoading) return <PageWrapper><LoadingSpinner className="py-32" size="lg" /></PageWrapper>
  if (isError)   return <PageWrapper><ErrorMessage message="Profile not found." onRetry={refetch} /></PageWrapper>

  const { user: profile, posts } = data
  const isOwnProfile = me?.id === profile?.id

  const compatScore = compatData?.score
  const compatLabel = compatData?.label

  return (
    <>
      <PageWrapper>
        {/* Back */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-brand-500 hover:text-brand-800 dark:hover:text-brand-200 mb-6 transition-colors"
        >
          <FiArrowLeft size={15} />
          Back
        </button>

        {/* Profile header */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10"
        >
          <div className="flex flex-col sm:flex-row sm:items-start gap-6">
            {/* Avatar */}
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-200 to-accent-200 dark:from-brand-700 dark:to-accent-800 flex items-center justify-center text-3xl font-bold text-brand-700 dark:text-brand-200 flex-shrink-0 overflow-hidden">
              {profile.avatar_url ? (
                <img src={resolveUrl(profile.avatar_url)} alt="" className="w-full h-full object-cover" />
              ) : (
                (profile.name?.[0] || profile.username?.[0] || '?').toUpperCase()
              )}
            </div>

            <div className="flex-1">
              <div className="flex flex-wrap items-start gap-3 mb-2">
                <div>
                  <h1 className="font-display text-3xl font-bold text-brand-900 dark:text-brand-100">
                    @{profile.username}
                  </h1>
                  {profile.name && (
                    <p className="text-brand-500 dark:text-brand-400">{profile.name}</p>
                  )}
                </div>

                {!isOwnProfile && (
                  <FollowButton
                    userId={profile.id}
                    initialIsFollowing={isFollowing ?? data.is_following}
                    onChanged={(action) => setIsFollowing(action === 'followed')}
                  />
                )}
              </div>

              {profile.bio && (
                <p className="text-sm text-brand-600 dark:text-brand-400 mb-3 max-w-md">
                  {profile.bio}
                </p>
              )}

              {/* Stats row */}
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="font-bold text-brand-900 dark:text-brand-100">{profile.follower_count}</span>
                  <span className="text-brand-500 ml-1">Followers</span>
                </div>
                <div>
                  <span className="font-bold text-brand-900 dark:text-brand-100">{profile.following_count}</span>
                  <span className="text-brand-500 ml-1">Following</span>
                </div>
                <div>
                  <span className="font-bold text-brand-900 dark:text-brand-100">{posts.length}</span>
                  <span className="text-brand-500 ml-1">Posts</span>
                </div>
              </div>
            </div>

            {/* Style compatibility badge */}
            {!isOwnProfile && compatScore !== undefined && compatScore !== null && (
              <div className="sm:ml-auto flex-shrink-0">
                <div className="card p-4 text-center min-w-[110px]">
                  <p className="text-2xl font-bold text-accent-700 dark:text-accent-400">
                    {Math.round(compatScore * 100)}%
                  </p>
                  <p className="text-xs text-brand-500 mt-0.5">{compatLabel}</p>
                  <p className="text-[10px] text-brand-500 mt-1">Style Match</p>
                </div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Posts grid */}
        {posts.length === 0 ? (
          <div className="text-center py-16 text-brand-500">
            <p className="text-4xl mb-3">👗</p>
            <p className="text-sm">No posts yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {posts.map(post => (
              <FeedCard
                key={post.id}
                post={post}
                onRemixClick={(p) => setRemixTarget(p)}
              />
            ))}
          </div>
        )}
      </PageWrapper>

      <RemixResultModal
        open={!!remixTarget}
        onClose={() => setRemixTarget(null)}
        post={remixTarget}
      />
    </>
  )
}
