import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FiUserPlus, FiUserCheck } from 'react-icons/fi'
import { followUser, unfollowUser } from '../../api/social.js'

export default function FollowButton({ userId, initialIsFollowing = false, onChanged }) {
  const [isFollowing, setIsFollowing] = useState(initialIsFollowing)
  const qc = useQueryClient()

  const followMutation = useMutation({
    mutationFn: () => followUser(userId),
    onMutate: () => setIsFollowing(true),   // optimistic
    onError:  () => setIsFollowing(false),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['social-profile'] })
      onChanged?.('followed', data)
    },
  })

  const unfollowMutation = useMutation({
    mutationFn: () => unfollowUser(userId),
    onMutate: () => setIsFollowing(false),  // optimistic
    onError:  () => setIsFollowing(true),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['social-profile'] })
      onChanged?.('unfollowed', data)
    },
  })

  const isPending = followMutation.isPending || unfollowMutation.isPending

  if (isFollowing) {
    return (
      <button
        onClick={() => unfollowMutation.mutate()}
        disabled={isPending}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-100 dark:bg-brand-800 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-700 hover:bg-red-50 hover:text-red-600 hover:border-red-200 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition-all disabled:opacity-50"
      >
        <FiUserCheck size={13} />
        {isPending ? '...' : 'Following'}
      </button>
    )
  }

  return (
    <button
      onClick={() => followMutation.mutate()}
      disabled={isPending}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-900 dark:bg-brand-100 text-white dark:text-brand-900 hover:bg-brand-700 dark:hover:bg-brand-300 transition-all disabled:opacity-50"
    >
      <FiUserPlus size={13} />
      {isPending ? '...' : 'Follow'}
    </button>
  )
}
