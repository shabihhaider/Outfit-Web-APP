export default function PageWrapper({ children, className = '' }) {
  return (
    <main className={`max-w-6xl mx-auto px-4 sm:px-6 py-8 min-h-screen animate-page-enter ${className}`}>
      {children}
    </main>
  )
}
