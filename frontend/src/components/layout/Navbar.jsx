import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiHome, FiGrid, FiStar, FiCalendar, FiBookmark, FiClock, FiLogOut, FiEdit3, FiMenu, FiX, FiUsers, FiSettings, FiBell } from 'react-icons/fi'
import ThemeToggle from '../ui/ThemeToggle.jsx'
import NotificationsPanel from '../ui/NotificationsPanel.jsx'
import { getNotificationCount } from '../../api/notifications.js'
import { resolveUrl } from '../../utils/resolveUrl.js'

const NAV_LINKS = [
  { to: '/dashboard',       label: 'Dashboard', Icon: FiHome },
  { to: '/wardrobe',        label: 'Wardrobe',  Icon: FiGrid },
  { to: '/feed',            label: 'Feed',      Icon: FiUsers },
  { to: '/recommendations', label: 'Recommend', Icon: FiStar },
  { to: '/editor',          label: 'Editor',    Icon: FiEdit3 },
  { to: '/calendar',        label: 'Calendar',  Icon: FiCalendar },
  { to: '/outfits/saved',   label: 'Saved',     Icon: FiBookmark },
  { to: '/outfits/history', label: 'History',   Icon: FiClock },
]

export default function Navbar() {
  const { user, logoutUser } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [avatarError, setAvatarError] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)

  const { data: countData } = useQuery({
    queryKey: ['notifications-count'],
    queryFn:  getNotificationCount,
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  })
  const unreadCount = countData?.unread_count ?? 0

  const location = useLocation()

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  // Reset error state whenever the avatar URL changes (new upload)
  useEffect(() => { setAvatarError(false) }, [user?.avatar_url])

  function handleLogout() {
    if (!window.confirm('Log out of OutfitAI?')) return
    logoutUser()
    navigate('/login')
  }

  return (
    <>
      <nav className="sticky top-0 z-40 bg-white/70 dark:bg-brand-900/70 backdrop-blur-xl border-b border-brand-100/60 dark:border-brand-800/40" aria-label="Main navigation">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="h-16 flex items-center justify-between">
            {/* Logo */}
            <NavLink to="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-brand-900 dark:bg-brand-100 flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-white dark:text-brand-900">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span className="hidden sm:block font-display text-xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
                Outfit<span className="text-accent-700">AI</span>
              </span>
            </NavLink>

            {/* Desktop nav — icons with labels at lg+ */}
            <div className="hidden md:flex items-center gap-1">
              {NAV_LINKS.map(link => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  title={link.label}
                  className={({ isActive }) =>
                    `relative group flex items-center gap-1.5 px-2.5 h-9 rounded-xl transition-all duration-200 ${isActive
                      ? 'text-brand-900 dark:text-brand-100'
                      : 'text-brand-500 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-200'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <link.Icon size={17} className="flex-shrink-0" />
                      <span className="hidden lg:block text-xs font-medium">{link.label}</span>
                      {isActive && (
                        <motion.div
                          layoutId="nav-indicator"
                          className="absolute inset-0 bg-brand-900/[0.08] dark:bg-brand-100/[0.1] rounded-xl -z-10"
                          transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }}
                        />
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-1">
              {/* Bell */}
              <button
                onClick={() => setNotifOpen(o => !o)}
                className="relative flex items-center justify-center w-9 h-9 rounded-xl text-brand-500 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-200 transition-colors hover:bg-brand-100/60 dark:hover:bg-brand-800/30"
                aria-label={unreadCount > 0 ? `Notifications, ${unreadCount > 9 ? '9+' : unreadCount} unread` : 'Notifications'}
                title="Notifications"
              >
                <FiBell size={17} />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 min-w-[14px] h-3.5 flex items-center justify-center bg-accent-500 text-white text-[9px] font-bold rounded-full px-0.5 leading-none">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              <ThemeToggle />

              {/* Avatar / Settings */}
              <NavLink
                to="/settings"
                title="Profile Settings"
                className="hidden sm:flex items-center justify-center w-9 h-9 rounded-xl overflow-hidden transition-all duration-200 hover:ring-2 hover:ring-accent-400 ring-offset-1 ring-offset-white dark:ring-offset-brand-950"
              >
                {user?.avatar_url && !avatarError ? (
                  <img
                    src={resolveUrl(user.avatar_url)}
                    alt=""
                    className="w-full h-full object-cover"
                    onError={() => setAvatarError(true)}
                  />
                ) : (
                  <div className="w-full h-full rounded-xl bg-brand-200 dark:bg-brand-700 flex items-center justify-center text-xs font-bold text-brand-600 dark:text-brand-300">
                    {(user?.name?.[0] || user?.email?.[0] || '?').toUpperCase()}
                  </div>
                )}
              </NavLink>

              <button
                onClick={handleLogout}
                className="hidden sm:flex items-center justify-center w-9 h-9 rounded-xl text-brand-500 hover:text-red-500 dark:text-brand-400 dark:hover:text-red-400 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20"
                title="Logout"
              >
                <FiLogOut size={17} />
              </button>

              {/* Mobile hamburger */}
              <button
                onClick={() => setMobileOpen(o => !o)}
                className="md:hidden p-2 rounded-lg text-brand-500 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors"
                aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={mobileOpen}
              >
                {mobileOpen ? <FiX size={20} /> : <FiMenu size={20} />}
              </button>
            </div>
          </div>
        </div>
      </nav>

      <NotificationsPanel open={notifOpen} onClose={() => setNotifOpen(false)} />

      {/* Mobile slide-down menu */}
      <AnimatePresence>
        {mobileOpen && (
          <>
          {/* Backdrop to dismiss on tap */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="md:hidden fixed inset-0 top-16 z-20 bg-black/20"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="md:hidden fixed top-16 inset-x-0 z-30 bg-white/95 dark:bg-brand-900/95 backdrop-blur-xl border-b border-brand-100 dark:border-brand-800 overflow-hidden"
          >
            <div className="px-4 py-3 space-y-1">
              {NAV_LINKS.map((link, i) => (
                <motion.div
                  key={link.to}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <NavLink
                    to={link.to}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                        ? 'bg-brand-900/[0.06] dark:bg-brand-100/[0.08] text-brand-900 dark:text-brand-100'
                        : 'text-brand-500 dark:text-brand-400'
                      }`
                    }
                  >
                    <link.Icon size={16} />
                    <span>{link.label}</span>
                  </NavLink>
                </motion.div>
              ))}
              <div className="pt-2 mt-2 border-t border-brand-100 dark:border-brand-800 space-y-1">
                <NavLink
                  to="/settings"
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                      ? 'bg-brand-900/[0.06] dark:bg-brand-100/[0.08] text-brand-900 dark:text-brand-100'
                      : 'text-brand-500 dark:text-brand-400'
                    }`
                  }
                >
                  <FiSettings size={16} />
                  <span>Settings</span>
                </NavLink>
                <button
                  onClick={() => { setMobileOpen(false); handleLogout() }}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-red-500 w-full"
                >
                  <FiLogOut size={16} />
                  <span>Logout</span>
                </button>
              </div>
            </div>
          </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
