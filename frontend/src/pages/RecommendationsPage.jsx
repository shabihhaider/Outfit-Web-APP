import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiZap } from 'react-icons/fi'
import { getRecommendations, getAroundItem } from '../api/recommendations.js'
import { getItems } from '../api/wardrobe.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import OccasionPicker from '../components/recommendations/OccasionPicker.jsx'
import LocationToggle from '../components/recommendations/LocationToggle.jsx'
import WeatherCard from '../components/recommendations/WeatherCard.jsx'
import OutfitCard from '../components/recommendations/OutfitCard.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'

function OutfitSkeleton() {
  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="skeleton h-6 w-16 rounded-lg" />
        <div className="skeleton h-4 w-28" />
      </div>
      <div className="flex gap-3">
        {[1,2,3].map(i => <div key={i} className="skeleton w-20 h-20 rounded-xl" />)}
      </div>
      <div className="skeleton h-1.5 w-full rounded-lg" />
    </div>
  )
}

export default function RecommendationsPage() {
  const location = useLocation()
  const anchorItemId = location.state?.anchorItemId ?? null

  const [occasion, setOccasionRaw] = useState(() => sessionStorage.getItem('rec_occasion') || '')
  const [weatherParams, setWeatherParamsRaw] = useState(() => {
    const saved = sessionStorage.getItem('rec_weather')
    return saved ? JSON.parse(saved) : { temp_celsius: 25 }
  })
  const [results, setResultsRaw] = useState(() => {
    const cached = sessionStorage.getItem('rec_results')
    return cached ? JSON.parse(cached) : null
  })
  const [detectedTemp, setDetectedTemp] = useState(null)
  const [locationName, setLocationName] = useState(null)

  function setResults(val) {
    setResultsRaw(val)
    if (val) sessionStorage.setItem('rec_results', JSON.stringify(val))
  }

  function setOccasion(val) {
    setOccasionRaw(val)
    sessionStorage.setItem('rec_occasion', val)
  }
  function setWeatherParams(val) {
    setWeatherParamsRaw(val)
    sessionStorage.setItem('rec_weather', JSON.stringify(val))
  }

  const { data: wardrobeData } = useQuery({
    queryKey: ['wardrobe'],
    queryFn: getItems,
    enabled: !!anchorItemId,
  })
  const anchorItem = wardrobeData?.items?.find(i => i.id === anchorItemId)

  const mutation = useMutation({
    mutationFn: (params) => {
      if (anchorItemId) return getAroundItem(anchorItemId, params)
      return getRecommendations(params)
    },
    onSuccess: (data) => {
      setResults(data)
      if (mutation.variables?.lat && mutation.variables?.lon) {
        setDetectedTemp(data.temperature_used)
      }
    },
  })

  function handleTempChange(params) {
    setWeatherParams(params)
    if (params.lat && params.lon) {
      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${params.lat}&lon=${params.lon}&format=json`)
        .then(r => r.json())
        .then(d => {
          const city = d.address?.city || d.address?.town || d.address?.village || d.address?.hamlet || 'Your location'
          setLocationName(city)
        })
        .catch(() => setLocationName('Your location'))
      fetch(`https://api.open-meteo.com/v1/forecast?latitude=${params.lat}&longitude=${params.lon}&current_weather=true`)
        .then(r => r.json())
        .then(d => setDetectedTemp(Math.round(d.current_weather.temperature)))
        .catch(() => {})
    } else {
      setDetectedTemp(null)
    }
  }

  function handleGetOutfits() {
    if (!occasion) return
    mutation.mutate({ occasion, ...weatherParams })
  }

  const outfits = results?.outfits ?? results?.recommendations ?? []
  const hasLowConfidence = results?.has_low_confidence

  return (
    <PageWrapper>
      <div className="mb-8">
        <p className="label-xs mb-1">Recommendations</p>
        <h1 className="font-display text-4xl sm:text-5xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
          Get Recommendations
        </h1>
        <p className="text-brand-500 dark:text-brand-400 mt-1">Let AI build the perfect outfit for you</p>
      </div>

      {/* Anchor item banner */}
      {anchorItem && (
        <div className="card p-4 mb-6 flex items-center gap-4 border-accent-300/40 dark:border-accent-700/40 bg-accent-50/50 dark:bg-accent-900/10">
          <div className="w-14 h-14 rounded-xl overflow-hidden bg-white dark:bg-brand-800 border border-accent-200/60 dark:border-accent-700/40">
            {anchorItem.image_url && (
              <img
                src={`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}${anchorItem.image_url}`}
                alt={anchorItem.category}
                className="w-full h-full object-cover"
              />
            )}
          </div>
          <div>
            <p className="text-sm font-semibold text-accent-700 dark:text-accent-400">Building outfit around:</p>
            <p className="text-xs text-accent-600 dark:text-accent-500 capitalize">{anchorItem.category} \u00B7 {anchorItem.formality}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: controls */}
        <div className="lg:col-span-1 space-y-6">
          <OccasionPicker value={occasion} onChange={setOccasion} />
          <LocationToggle onTempChange={handleTempChange} />
          <WeatherCard detectedTemp={detectedTemp} locationName={locationName} />

          <button
            onClick={handleGetOutfits}
            disabled={!occasion || mutation.isPending}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3.5 text-base group"
          >
            {mutation.isPending ? (
              <><LoadingSpinner size="sm" /> Finding outfits...</>
            ) : (
              <>
                <FiZap size={16} className="transition-transform group-hover:rotate-12" />
                Get Outfits
              </>
            )}
          </button>
        </div>

        {/* Right: results */}
        <div className="lg:col-span-2 space-y-5">
          {mutation.isPending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">
              <OutfitSkeleton />
              <OutfitSkeleton />
              <OutfitSkeleton />
            </motion.div>
          )}

          {mutation.isError && (
            <ErrorMessage
              message={
                mutation.error?.response?.status === 422 && occasion !== 'casual'
                  ? `Not enough ${occasion} items in your wardrobe. Go to Wardrobe and edit item formality to tag some as "${occasion === 'wedding' ? 'formal' : occasion}" or "both".`
                  : mutation.error?.response?.data?.error ||
                    mutation.error?.response?.data?.message ||
                    'Could not get recommendations. Make sure your wardrobe has enough items.'
              }
            />
          )}

          {!mutation.isPending && results && (
            <>
              {hasLowConfidence && (
                <div className="p-4 bg-amber-50/60 dark:bg-amber-900/10 border border-amber-200/40 dark:border-amber-800/30 rounded-xl text-sm text-amber-700 dark:text-amber-300">
                  These outfits have low compatibility scores. Consider uploading more items for better results.
                </div>
              )}

              {outfits.length === 0 ? (
                <EmptyState
                  icon="🤔"
                  title="No outfits found"
                  description="Try a different occasion or upload more clothing items to your wardrobe."
                />
              ) : (
                outfits.map((outfit, i) => (
                  <OutfitCard key={i} outfit={{...outfit, temperature_used: results.temperature_used}} occasion={occasion} />
                ))
              )}
            </>
          )}

          {!mutation.isPending && !results && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-2xl bg-brand-100/60 dark:bg-brand-800/30 flex items-center justify-center text-3xl mb-4">
                <FiZap className="text-brand-300 dark:text-brand-600" size={28} />
              </div>
              <p className="text-brand-500 dark:text-brand-400 text-sm">Select an occasion and click &ldquo;Get Outfits&rdquo; to start</p>
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  )
}
