import WardrobeCard from './WardrobeCard.jsx'
import EmptyState from '../ui/EmptyState.jsx'

export default function WardrobeGrid({ items, onDelete, onUpload }) {
  if (!items || items.length === 0) {
    return (
      <EmptyState
        icon="👔"
        title="Your wardrobe is empty"
        description="Upload your first item to get started. Our AI will automatically detect the category."
        action={{ label: '📸 Upload Item', onClick: onUpload }}
      />
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {items.map(item => (
        <WardrobeCard key={item.id} item={item} onDelete={onDelete} />
      ))}
    </div>
  )
}
