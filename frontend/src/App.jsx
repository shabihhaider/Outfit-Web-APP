import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import AuthGuard from './guards/AuthGuard.jsx'
import ErrorBoundary from './components/ui/ErrorBoundary.jsx'
import ConsentBanner from './components/ui/ConsentBanner.jsx'
import Navbar from './components/layout/Navbar.jsx'
import InitialWarmupOverlay from './components/ui/InitialWarmupOverlay.jsx'

// ── Lazy-loaded pages — each becomes its own JS chunk ─────────────────────────
const LoginPage            = lazy(() => import('./pages/LoginPage.jsx'))
const RegisterPage         = lazy(() => import('./pages/RegisterPage.jsx'))
const ForgotPasswordPage   = lazy(() => import('./pages/ForgotPasswordPage.jsx'))
const ResetPasswordPage    = lazy(() => import('./pages/ResetPasswordPage.jsx'))
const DashboardPage        = lazy(() => import('./pages/DashboardPage.jsx'))
const WardrobePage         = lazy(() => import('./pages/WardrobePage.jsx'))
const RecommendationsPage  = lazy(() => import('./pages/RecommendationsPage.jsx'))
const SavedOutfitsPage     = lazy(() => import('./pages/SavedOutfitsPage.jsx'))
const HistoryPage          = lazy(() => import('./pages/HistoryPage.jsx'))
const CalendarPage         = lazy(() => import('./pages/CalendarPage.jsx'))
const OutfitEditorPage     = lazy(() => import('./pages/OutfitEditorPage.jsx'))
const SocialFeedPage       = lazy(() => import('./pages/SocialFeedPage.jsx'))
const PublicProfilePage    = lazy(() => import('./pages/PublicProfilePage.jsx'))
const ProfileSettingsPage  = lazy(() => import('./pages/ProfileSettingsPage.jsx'))
const OnboardingFlow       = lazy(() => import('./components/onboarding/OnboardingFlow.jsx'))
const NotFoundPage         = lazy(() => import('./pages/NotFoundPage.jsx'))

function PageSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-50 dark:bg-brand-950">
      <div className="w-8 h-8 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
    </div>
  )
}

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-brand-50 dark:bg-brand-950">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-brand-900 focus:text-white focus:rounded-lg focus:text-sm focus:font-medium">
        Skip to content
      </a>
      <Navbar />
      <InitialWarmupOverlay />
      <main id="main-content">
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </main>
      <ConsentBanner />
    </div>
  )
}

export default function App() {
  const { isAuthenticated } = useAuth()

  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
        } />
        <Route path="/register" element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />
        } />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Onboarding — protected but no Navbar */}
        <Route path="/onboarding" element={
          <AuthGuard>
            <OnboardingFlow />
          </AuthGuard>
        } />

        {/* Protected routes */}
        <Route path="/dashboard" element={
          <AuthGuard>
            <Layout><DashboardPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/wardrobe" element={
          <AuthGuard>
            <Layout><WardrobePage /></Layout>
          </AuthGuard>
        } />
        <Route path="/recommendations" element={
          <AuthGuard>
            <Layout><RecommendationsPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/outfits/saved" element={
          <AuthGuard>
            <Layout><SavedOutfitsPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/outfits/history" element={
          <AuthGuard>
            <Layout><HistoryPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/calendar" element={
          <AuthGuard>
            <Layout><CalendarPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/editor" element={
          <AuthGuard>
            <Layout><OutfitEditorPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/feed" element={
          <AuthGuard>
            <Layout><SocialFeedPage /></Layout>
          </AuthGuard>
        } />
        <Route path="/u/:username" element={
          <AuthGuard>
            <Layout><PublicProfilePage /></Layout>
          </AuthGuard>
        } />
        <Route path="/settings" element={
          <AuthGuard>
            <Layout><ProfileSettingsPage /></Layout>
          </AuthGuard>
        } />

        {/* Root redirect */}
        <Route path="/" element={
          <Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />
        } />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
