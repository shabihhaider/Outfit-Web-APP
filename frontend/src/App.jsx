import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import AuthGuard from './guards/AuthGuard.jsx'
import ErrorBoundary from './components/ui/ErrorBoundary.jsx'
import ConsentBanner from './components/ui/ConsentBanner.jsx'
import Navbar from './components/layout/Navbar.jsx'
import InitialWarmupOverlay from './components/ui/InitialWarmupOverlay.jsx'

import LoginPage from './pages/LoginPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import WardrobePage from './pages/WardrobePage.jsx'
import RecommendationsPage from './pages/RecommendationsPage.jsx'
import SavedOutfitsPage from './pages/SavedOutfitsPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import OutfitEditorPage from './pages/OutfitEditorPage.jsx'
import SocialFeedPage from './pages/SocialFeedPage.jsx'
import PublicProfilePage from './pages/PublicProfilePage.jsx'
import ProfileSettingsPage from './pages/ProfileSettingsPage.jsx'
import OnboardingFlow from './components/onboarding/OnboardingFlow.jsx'
import ForgotPasswordPage from './pages/ForgotPasswordPage.jsx'
import ResetPasswordPage from './pages/ResetPasswordPage.jsx'

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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
