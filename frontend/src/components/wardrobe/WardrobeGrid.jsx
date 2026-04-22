import WardrobeCard from './WardrobeCard.jsx'
import EmptyState from '../ui/EmptyState.jsx'

const CATEGORY_LABELS = {
  top:      { noun: 'tops',       upload: 'Upload a Top' },
  bottom:   { noun: 'bottoms',    upload: 'Upload a Bottom' },
  outwear:  { noun: 'outerwear',  upload: 'Upload Outerwear' },
  shoes:    { noun: 'shoes',      upload: 'Upload Shoes' },
  dress:    { noun: 'dresses',    upload: 'Upload a Dress' },
  jumpsuit: { noun: 'jumpsuits',  upload: 'Upload a Jumpsuit' },
}

export default function WardrobeGrid({ items, onDelete, onUpload, selectMode, selectedIds, onToggleSelect, filter, isArchived }) {
  if (!items || items.length === 0) {
    if (isArchived) {
      return (
        <EmptyState
          icon="📦"
          title="No archived items"
          description="Items you archive will appear here. Archived items don't count toward your 50-item limit."
        />
      )
    }
    const cat = filter && filter !== 'all' ? CATEGORY_LABELS[filter] : null
    return (
      <EmptyState
        icon="👔"
        title={cat ? `No ${cat.noun} yet` : 'Your wardrobe is empty'}
        description={cat
          ? `You have no ${cat.noun} in your wardrobe. Upload one to get started.`
          : 'Upload your first item to get started. Our AI will automatically detect the category.'}
        action={{ label: cat ? `📸 ${cat.upload}` : '📸 Upload Item', onClick: onUpload }}
      />
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {items.map(item => (
        <WardrobeCard
          key={item.id}
          item={item}
          onDelete={onDelete}
          selectMode={selectMode}
          selected={selectedIds?.has(item.id) ?? false}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  )
}
