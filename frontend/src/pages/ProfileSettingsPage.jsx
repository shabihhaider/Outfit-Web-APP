import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiCamera, FiUser, FiSave, FiCheck, FiAlertCircle } from 'react-icons/fi'
import { getMyProfile, updateProfile, uploadAvatar } from '../api/social.js'
import { getPersonPhoto, uploadPersonPhoto } from '../api/vto.js'
import { useAuth } from '../context/AuthContext.jsx'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const TABS = [
  { key: 'account',  label: 'Account Info' },
  { key: 'avatar',   label: 'Profile Photo' },
  { key: 'vto',      label: 'VTO Body Photo' },
]

export default function ProfileSettingsPage() {
  const { user: authUser, updateUser } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState('account')

  const { data: profile, isLoading } = useQuery({
    queryKey: ['my-profile'],
    queryFn: getMyProfile,
  })

  if (isLoading) return <PageWrapper><LoadingSpinner className="py-24" size="lg" /></PageWrapper>

  return (
    <PageWrapper>
      <div className="mb-8">
        <p className="label-xs mb-1">Settings</p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-brand-900 dark:text-brand-100 tracking-tight">
          Profile Settings
        </h1>
      </div>

      <div className="max-w-2xl mx-auto">
        {/* Tab bar */}
        <div className="flex gap-1 bg-brand-100/60 dark:bg-brand-900/30 rounded-xl p-1 mb-8">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t.key
                  ? 'bg-white dark:bg-brand-800 text-brand-900 dark:text-brand-100 shadow-sm'
                  : 'text-brand-500 hover:text-brand-700 dark:hover:text-brand-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'account'  && <AccountTab profile={profile} qc={qc} updateUser={updateUser} />}
        {tab === 'avatar'   && <AvatarTab  profile={profile} qc={qc} updateUser={updateUser} />}
        {tab === 'vto'      && <VtoTab />}
      </div>
    </PageWrapper>
  )
}

/* ── Account Info tab ──────────────────────────────────────────────────────── */

function AccountTab({ profile, qc, updateUser }) {
  const [form, setForm] = useState({
    name:     profile?.name     ?? '',
    username: profile?.username ?? '',
    bio:      profile?.bio      ?? '',
    gender:   profile?.gender   ?? 'unisex',
    is_public: profile?.is_public ?? true,
  })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => updateProfile(form),
    onSuccess: (data) => {
      setSaved(true)
      setError('')
      updateUser({ name: data.name, username: data.username, bio: data.bio, gender: data.gender })
      qc.invalidateQueries({ queryKey: ['my-profile'] })
      setTimeout(() => setSaved(false), 2500)
    },
    onError: (err) => {
      setError(err?.response?.data?.error ?? 'Failed to save. Please try again.')
    },
  })

  return (
    <div className="card p-6 space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="Full Name" value={form.name} onChange={v => setForm(p => ({ ...p, name: v }))} placeholder="Your display name" />
        <Field label="Username" value={form.username} onChange={v => setForm(p => ({ ...p, username: v.toLowerCase() }))} placeholder="e.g. farhan_malik" />
      </div>

      <div>
        <label className="block text-xs font-bold uppercase tracking-widest text-brand-400 mb-1.5">Bio</label>
        <textarea
          value={form.bio}
          onChange={e => setForm(p => ({ ...p, bio: e.target.value }))}
          maxLength={150}
          rows={3}
          placeholder="A short bio about your style…"
          className="w-full px-4 py-3 rounded-2xl border border-brand-200 dark:border-brand-700 bg-white dark:bg-brand-900 text-brand-900 dark:text-brand-100 text-sm placeholder:text-brand-300 dark:placeholder:text-brand-600 focus:outline-none focus:ring-2 focus:ring-accent-400 resize-none"
        />
        <p className="text-[10px] text-brand-400 text-right mt-1">{form.bio.length}/150</p>
      </div>

      <div>
        <label className="block text-xs font-bold uppercase tracking-widest text-brand-400 mb-2">Gender</label>
        <div className="flex gap-2">
          {['men', 'women', 'unisex'].map(g => (
            <button
              key={g}
              onClick={() => setForm(p => ({ ...p, gender: g }))}
              className={`flex-1 py-2.5 rounded-xl text-sm font-medium capitalize border transition-all ${
                form.gender === g
                  ? 'bg-brand-900 dark:bg-brand-100 text-white dark:text-brand-900 border-brand-900 dark:border-brand-100'
                  : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-brand-800 dark:text-brand-200">Public Profile</p>
          <p className="text-xs text-brand-400">Let others discover and follow you</p>
        </div>
        <button
          onClick={() => setForm(p => ({ ...p, is_public: !p.is_public }))}
          className={`w-12 h-6 rounded-full transition-colors relative ${form.is_public ? 'bg-accent-500' : 'bg-brand-300 dark:bg-brand-700'}`}
        >
          <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all ${form.is_public ? 'left-7' : 'left-1'}`} />
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
          <FiAlertCircle size={15} />
          {error}
        </div>
      )}

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="w-full btn-primary h-11 rounded-2xl flex items-center justify-center gap-2 font-medium disabled:opacity-50"
      >
        {saved ? <><FiCheck size={16} /> Saved!</> : mutation.isPending ? 'Saving…' : <><FiSave size={16} /> Save Changes</>}
      </button>
    </div>
  )
}

/* ── Avatar tab ────────────────────────────────────────────────────────────── */

function AvatarTab({ profile, qc, updateUser }) {
  const fileRef = useRef(null)
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const currentAvatar = profile?.avatar_url ? `${API_URL}${profile.avatar_url}` : null
  const displayName   = profile?.name || profile?.username || 'U'

  const mutation = useMutation({
    mutationFn: () => uploadAvatar(file),
    onSuccess: (data) => {
      setSaved(true)
      setError('')
      setPreview(null)
      setFile(null)
      updateUser({ avatar_url: data.avatar_url })
      qc.invalidateQueries({ queryKey: ['my-profile'] })
      setTimeout(() => setSaved(false), 2500)
    },
    onError: (err) => {
      setError(err?.response?.data?.error ?? 'Upload failed. Please try again.')
    },
  })

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setSaved(false)
    setError('')
    const reader = new FileReader()
    reader.onload = ev => setPreview(ev.target.result)
    reader.readAsDataURL(f)
  }

  return (
    <div className="card p-6 space-y-6">
      <p className="text-sm text-brand-500 dark:text-brand-400">
        Your profile photo appears next to your posts in the social feed and in your profile.
      </p>

      {/* Preview */}
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-brand-100 dark:border-brand-800 bg-brand-200 dark:bg-brand-700 flex items-center justify-center shadow-elevated">
            {preview ? (
              <img src={preview} alt="Preview" className="w-full h-full object-cover" />
            ) : currentAvatar ? (
              <img src={currentAvatar} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <span className="text-5xl font-bold text-brand-500 dark:text-brand-400">
                {displayName[0]?.toUpperCase()}
              </span>
            )}
          </div>
          <button
            onClick={() => fileRef.current?.click()}
            className="absolute bottom-1 right-1 w-9 h-9 rounded-full bg-brand-900 dark:bg-brand-100 text-brand-100 dark:text-brand-900 flex items-center justify-center shadow-lg hover:scale-110 transition-transform"
          >
            <FiCamera size={15} />
          </button>
        </div>

        <div className="text-center">
          <p className="font-semibold text-brand-800 dark:text-brand-200">{displayName}</p>
          {profile?.username && <p className="text-sm text-brand-400">@{profile.username}</p>}
        </div>
      </div>

      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleFile} />

      <button
        onClick={() => fileRef.current?.click()}
        className="w-full btn-secondary h-11 rounded-2xl flex items-center justify-center gap-2"
      >
        <FiCamera size={16} />
        {currentAvatar ? 'Change Photo' : 'Upload Photo'}
      </button>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
          <FiAlertCircle size={15} />
          {error}
        </div>
      )}

      {file && (
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="w-full btn-primary h-11 rounded-2xl flex items-center justify-center gap-2 font-medium disabled:opacity-50"
        >
          {saved ? <><FiCheck size={16} /> Saved!</> : mutation.isPending ? 'Uploading…' : <><FiSave size={16} /> Save Photo</>}
        </button>
      )}
    </div>
  )
}

/* ── VTO Body Photo tab ────────────────────────────────────────────────────── */

function VtoTab() {
  const fileRef = useRef(null)
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const qc = useQueryClient()

  const { data: vtoData } = useQuery({
    queryKey: ['vto-person-photo'],
    queryFn: getPersonPhoto,
  })

  const currentPhoto = vtoData?.photo_url ? `${API_URL}${vtoData.photo_url}` : null

  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('photo', file)
      return uploadPersonPhoto(fd)
    },
    onSuccess: () => {
      setSaved(true)
      setError('')
      setPreview(null)
      setFile(null)
      qc.invalidateQueries({ queryKey: ['vto-person-photo'] })
      setTimeout(() => setSaved(false), 2500)
    },
    onError: (err) => {
      setError(err?.response?.data?.error ?? 'Upload failed. Please try again.')
    },
  })

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setSaved(false)
    setError('')
    const reader = new FileReader()
    reader.onload = ev => setPreview(ev.target.result)
    reader.readAsDataURL(f)
  }

  return (
    <div className="card p-6 space-y-6">
      <div className="p-4 bg-accent-50 dark:bg-accent-900/20 border border-accent-100 dark:border-accent-800/40 rounded-2xl text-sm text-accent-700 dark:text-accent-300 space-y-1">
        <p className="font-semibold">What is a VTO Body Photo?</p>
        <p className="text-accent-600 dark:text-accent-400">Upload a clear, full-body photo of yourself. This is used by our Virtual Try-On feature to show how clothing items look on you. For best results, stand straight against a plain background.</p>
      </div>

      {/* Preview */}
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-48 h-64 rounded-2xl overflow-hidden border-2 border-brand-100 dark:border-brand-800 bg-brand-100/40 dark:bg-brand-800/20 flex items-center justify-center">
          {preview ? (
            <img src={preview} alt="Preview" className="w-full h-full object-cover" />
          ) : currentPhoto ? (
            <img src={currentPhoto} alt="Current VTO photo" className="w-full h-full object-cover" />
          ) : (
            <div className="flex flex-col items-center gap-3 text-brand-300 dark:text-brand-600">
              <FiUser size={48} />
              <p className="text-xs font-medium text-center px-4">No body photo uploaded yet</p>
            </div>
          )}
          <button
            onClick={() => fileRef.current?.click()}
            className="absolute bottom-2 right-2 w-9 h-9 rounded-full bg-brand-900 dark:bg-brand-100 text-brand-100 dark:text-brand-900 flex items-center justify-center shadow-lg hover:scale-110 transition-transform"
          >
            <FiCamera size={15} />
          </button>
        </div>
        {vtoData?.has_photo && !preview && (
          <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">✓ VTO photo uploaded</p>
        )}
      </div>

      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleFile} />

      <button
        onClick={() => fileRef.current?.click()}
        className="w-full btn-secondary h-11 rounded-2xl flex items-center justify-center gap-2"
      >
        <FiCamera size={16} />
        {vtoData?.has_photo ? 'Replace Body Photo' : 'Upload Body Photo'}
      </button>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
          <FiAlertCircle size={15} />
          {error}
        </div>
      )}

      {file && (
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="w-full btn-primary h-11 rounded-2xl flex items-center justify-center gap-2 font-medium disabled:opacity-50"
        >
          {saved ? <><FiCheck size={16} /> Saved!</> : mutation.isPending ? 'Uploading…' : <><FiSave size={16} /> Save Photo</>}
        </button>
      )}
    </div>
  )
}

/* ── Shared ───────────────────────────────────────────────────────────────── */

function Field({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="block text-xs font-bold uppercase tracking-widest text-brand-400 mb-1.5">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-3 rounded-2xl border border-brand-200 dark:border-brand-700 bg-white dark:bg-brand-900 text-brand-900 dark:text-brand-100 text-sm placeholder:text-brand-300 dark:placeholder:text-brand-600 focus:outline-none focus:ring-2 focus:ring-accent-400"
      />
    </div>
  )
}
