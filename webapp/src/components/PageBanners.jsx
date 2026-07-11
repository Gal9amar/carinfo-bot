import { useState, useEffect } from 'react'
import { fetchBanners } from '../api.js'

export default function PageBanners({ page, onNavigate }) {
  const [banners, setBanners] = useState([])
  useEffect(() => { fetchBanners(page).then(setBanners).catch(() => setBanners([])) }, [page])

  if (!onNavigate || banners.length === 0) return null

  function handleClick(b) {
    if (b.link_type === 'product') onNavigate('packages', { highlightProductId: b.link_value })
    else onNavigate(b.link_value || 'packages')
  }

  return (
    <>
      {banners.map(b => (
        <button
          key={b.id}
          onClick={() => handleClick(b)}
          style={{
            display: 'flex', alignItems: 'center', gap: 14, width: '100%',
            background: b.image_url
              ? `linear-gradient(135deg, ${b.color_from}cc 0%, ${b.color_to}cc 100%), url(${b.image_url}) center/cover`
              : `linear-gradient(135deg, ${b.color_from} 0%, ${b.color_to} 100%)`,
            border: 'none', borderRadius: 16, padding: '14px 18px',
            marginBottom: 20, cursor: 'pointer', textAlign: 'right',
          }}
        >
          <span style={{ fontSize: 34, flexShrink: 0 }}>{b.icon}</span>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 15, marginBottom: 2 }}>
              {b.title}
            </div>
            {b.subtitle && (
              <div style={{ color: 'rgba(255,255,255,0.82)', fontSize: 12 }}>
                {b.subtitle}
              </div>
            )}
          </div>
        </button>
      ))}
    </>
  )
}
