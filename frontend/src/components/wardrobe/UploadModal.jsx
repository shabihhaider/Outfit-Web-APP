import { useState, useRef, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiUploadCloud, FiCheck, FiZap } from 'react-icons/fi'
import { uploadItem } from '../../api/wardrobe.js'
import { useAuth } from '../../context/AuthContext.jsx'
import LoadingSpinner from '../ui/LoadingSpinner.jsx'

const FORMALITIES = ['casual', 'formal', 'both']
const GENDERS = ['men', 'women', 'unisex']

export default function UploadModal({ open, onClose }) {
  const { user } = useAuth()
  const defaultGender = user?.gender || ''
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [formality, setFormality] = useState('casual')
  const [gender, setGender] = useState(defaultGender)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [uploadData, setUploadData] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: uploadItem,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] })
      setSuccess(`${data.category.charAt(0).toUpperCase() + data.category.slice(1)} added to your wardrobe!`)
      setUploadData(data)
      setFile(null)
      setPreview(null)
      setFormality('casual')
      setGender(defaultGender)
      setTimeout(() => {
        setSuccess('');
        setUploadData(null);
        onClose();
      }, 5000)
    },
    onError: (err) => {
      const msg = err.response?.data?.error || err.response?.data?.message || 'Upload failed. Please try again.'
      setError(msg)
    },
  })

  const handleFileSelect = useCallback((selectedFile) => {
    if (!selectedFile) return
    setError('')
    setFile(selectedFile)
    const url = URL.createObjectURL(selectedFile)
    setPreview(url)
  }, [])

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFileSelect(f)
  }

  function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!file) { setError('Please select an image.'); return }
    if (!formality) { setError('Please select a formality.'); return }
    if (!gender) { setError('Please select a gender.'); return }

    const fd = new FormData()
    fd.append('image', file)
    fd.append('formality', formality)
    fd.append('gender', gender)
    mutation.mutate(fd)
  }

  function handleClose() {
    setFile(null)
    setPreview(null)
    setFormality('casual')
    setGender(defaultGender)
    setError('')
    setSuccess('')
    setUploadData(null)
    onClose()
  }

  if (!open) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-950/60 backdrop-blur-md"
        onClick={handleClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="card w-full max-w-md shadow-modal max-h-[90vh] overflow-y-auto"
          onClick={e => e.stopPropagation()}
        >
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-2xl font-semibold text-brand-900 dark:text-brand-100">Upload Item</h2>
              <button onClick={handleClose} className="p-1.5 rounded-lg text-brand-500 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors">
                <FiX size={18} />
              </button>
            </div>

            {success ? (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="py-4"
              >
                <div className="text-center mb-6">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
                    <FiCheck className="text-emerald-600 dark:text-emerald-400" size={24} />
                  </div>
                  <p className="font-display text-xl font-semibold text-brand-900 dark:text-brand-100">{success}</p>
                  {uploadData?.bg_removed && (
                    <motion.div
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full bg-accent-100 dark:bg-accent-900/30 border border-accent-200/60 dark:border-accent-700/40"
                    >
                      <FiZap size={11} className="text-accent-700 dark:text-accent-400" />
                      <span className="text-xs font-medium text-accent-700 dark:text-accent-300">Atelier: Background removed</span>
                    </motion.div>
                  )}
                </div>

                {uploadData?.tips && uploadData.tips.length > 0 && (
                  <div className="space-y-2">
                    <p className="label-xs">Style tips</p>
                    {uploadData.tips.map((tip, i) => (
                      <div key={i} className="text-sm text-brand-600 dark:text-brand-400 flex gap-2.5 bg-brand-50/60 dark:bg-brand-800/30 rounded-xl p-3 border border-brand-100/40 dark:border-brand-700/30">
                        <span className="text-accent-700 font-bold mt-0.5">*</span>
                        <span>{tip}</span>
                      </div>
                    ))}
                  </div>
                )}

                <button onClick={handleClose} className="btn-primary w-full mt-6">Done</button>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Drop zone */}
                <div
                  className={`relative border-2 border-dashed rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden ${
                    dragging ? 'border-accent-400 bg-accent-50/50 dark:bg-accent-900/10' : 'border-brand-200 dark:border-brand-700 hover:border-brand-400 dark:hover:border-brand-500'
                  }`}
                  onDragOver={e => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {preview ? (
                    <div className="relative group">
                      <img src={preview} alt="Preview" className="w-full h-56 object-cover" />
                      <div className="absolute inset-0 bg-brand-900/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <span className="text-white text-sm font-medium bg-black/30 px-3 py-1.5 rounded-lg backdrop-blur-sm">Change image</span>
                      </div>
                    </div>
                  ) : (
                    <div className="py-12 flex flex-col items-center text-brand-500 dark:text-brand-400">
                      <FiUploadCloud size={32} className="mb-3 text-brand-300 dark:text-brand-600" />
                      <p className="text-sm font-medium text-brand-500 dark:text-brand-400">Drop image here or click to browse</p>
                      <p className="text-xs mt-1 text-brand-500 dark:text-brand-400">PNG, JPG, WEBP up to 10MB</p>
                    </div>
                  )}
                  <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={e => handleFileSelect(e.target.files[0])} />
                </div>

                <p className="text-xs text-brand-500 dark:text-brand-400 text-center">
                  Category will be auto-detected by AI
                </p>

                {/* Formality */}
                <div>
                  <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-2">Formality</label>
                  <div className="flex gap-2">
                    {FORMALITIES.map(f => (
                      <button
                        key={f}
                        type="button"
                        onClick={() => setFormality(f)}
                        className={`flex-1 py-2.5 rounded-xl text-sm font-medium border-2 transition-all duration-200 ${
                          formality === f
                            ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100 shadow-md'
                            : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400 dark:hover:border-brand-500'
                        }`}
                      >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Gender */}
                <div>
                  <label className="block text-sm font-medium text-brand-600 dark:text-brand-400 mb-2">Gender</label>
                  <div className="flex gap-2">
                    {GENDERS.map(g => (
                      <button
                        key={g}
                        type="button"
                        onClick={() => setGender(g)}
                        className={`flex-1 py-2.5 rounded-xl text-sm font-medium border-2 transition-all duration-200 ${
                          gender === g
                            ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100 shadow-md'
                            : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400 dark:hover:border-brand-500'
                        }`}
                      >
                        {g.charAt(0).toUpperCase() + g.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <div className="p-3 bg-red-50/80 dark:bg-red-900/15 border border-red-200/60 dark:border-red-800/40 rounded-xl text-red-700 dark:text-red-300 text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-2">
                <button type="button" onClick={handleClose} disabled={mutation.isPending} className="btn-secondary flex-1 py-3">
                  Cancel
                </button>
                <button type="submit" disabled={mutation.isPending} className="btn-primary flex-1 flex flex-col items-center justify-center gap-1 py-3 h-auto min-h-[52px]">
                  {mutation.isPending ? (
                    <>
                      <div className="flex items-center gap-2">
                        <LoadingSpinner size="sm" />
                        <span>Atelier Refining...</span>
                      </div>
                      <span className="text-[10px] opacity-60 font-medium">Removing background & analyzing style</span>
                    </>
                  ) : (
                    <div className="flex items-center gap-2">
                      <FiUploadCloud size={16} />
                      <span>Upload Item</span>
                    </div>
                  )}
                </button>
                </div>
              </form>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
