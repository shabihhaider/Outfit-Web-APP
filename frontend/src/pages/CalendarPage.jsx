import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { getPlans } from '../api/calendar.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import CalendarNav, { getWeekStart } from '../components/calendar/CalendarNav.jsx'
import CalendarGrid from '../components/calendar/CalendarGrid.jsx'
import CalendarWeekView from '../components/calendar/CalendarWeekView.jsx'
import PlanModal from '../components/calendar/PlanModal.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'

function toDateStr(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function CalendarPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [view, setView] = useState('month')
  const [weekStart, setWeekStart] = useState(() => getWeekStart(now))

  const [modalOpen, setModalOpen] = useState(false)
  const [selectedDate, setSelectedDate] = useState(null)
  const [selectedPlan, setSelectedPlan] = useState(null)

  // When navigating weeks, keep the month query in sync with the visible week
  useEffect(() => {
    if (view === 'week') {
      setYear(weekStart.getFullYear())
      setMonth(weekStart.getMonth())
    }
  }, [view, weekStart])

  const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`

  // Single month query — always enabled so data is ready when switching views
  const { data: monthData, isLoading, error, refetch } = useQuery({
    queryKey: ['calendar', monthStr],
    queryFn: () => getPlans(monthStr),
  })

  const allPlans = monthData?.plans ?? []

  // For week view: filter month plans to the 7-day window client-side
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekEnd.getDate() + 6)
  const weekStartStr = toDateStr(weekStart)
  const weekEndStr   = toDateStr(weekEnd)
  const weekPlans = allPlans.filter(p => p.plan_date >= weekStartStr && p.plan_date <= weekEndStr)

  const plans = view === 'week' ? weekPlans : allPlans

  function handleMonthChange(newYear, newMonth) {
    setYear(newYear)
    setMonth(newMonth)
  }

  function handleDayClick(dateStr, plan) {
    setSelectedDate(dateStr)
    setSelectedPlan(plan || null)
    setModalOpen(true)
  }

  function handleModalClose() {
    setModalOpen(false)
    setSelectedDate(null)
    setSelectedPlan(null)
  }

  // For PlanModal cache invalidation: use the month of the selected date
  const selectedMonth = selectedDate
    ? selectedDate.slice(0, 7)
    : monthStr

  const planCount = plans.length

  return (
    <PageWrapper>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10"
      >
        <p className="label-xs mb-1">Curation Planner</p>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="max-w-xl">
            <h1 className="font-display text-3xl sm:text-4xl lg:text-6xl font-bold text-brand-900 dark:text-brand-100 tracking-tight leading-tight">
              Outfit Calendar
            </h1>
            <p className="text-brand-500 dark:text-brand-400 mt-3 text-lg font-medium italic">
              {planCount > 0
                ? `You have ${planCount} ensemble${planCount !== 1 ? 's' : ''} orchestrated for this period.`
                : view === 'week'
                ? 'Plan your outfits for the week ahead.'
                : 'Orchestrate your daily ensembles for the month ahead.'
              }
            </p>
          </div>
          <CalendarNav
            year={year}
            month={month}
            onChange={handleMonthChange}
            view={view}
            onViewChange={setView}
            weekStart={weekStart}
            onWeekChange={setWeekStart}
          />
        </div>
      </motion.div>

      {/* Main Grid Area */}
      <div className="relative">
        <div className="absolute inset-0 bg-brand-50/20 dark:bg-brand-950/5 rounded-[40px] -z-10" />

        {isLoading && <LoadingSpinner className="py-32" size="lg" />}
        {error && <ErrorMessage message="An error occurred while retrieving your schedule." onRetry={refetch} />}

        {!isLoading && !error && (
          <motion.div
            key={view}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            {view === 'week' ? (
              <CalendarWeekView
                weekStart={weekStart}
                plans={plans}
                onDayClick={handleDayClick}
              />
            ) : (
              <CalendarGrid
                year={year}
                month={month}
                plans={plans}
                onDayClick={handleDayClick}
              />
            )}
          </motion.div>
        )}
      </div>

      <PlanModal
        open={modalOpen}
        date={selectedDate}
        existingPlan={selectedPlan}
        monthStr={selectedMonth}
        onClose={handleModalClose}
      />
    </PageWrapper>
  )
}
