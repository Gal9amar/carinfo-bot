import { useState, useEffect } from 'react'
import { fetchReportLayout } from '../api.js'

// Default order of the report sections (used until/unless the admin layout arrives).
export const DEFAULT_REPORT_ORDER = {
  summary: ['score', 'test', 'model_count', 'ownership', 'main_details', 'recalls', 'notes', 'garage', 'market', 'alerts', 'pdf', 'compare'],
  full: ['general', 'technical', 'wheels', 'equipment', 'safety', 'adas', 'history', 'recalls'],
}

// Admin-defined list [{id, visible}] -> ordered ids. Unknown ids are dropped, ids the layout
// misses are appended in default order; falls back to the default for a malformed layout.
function resolveOrder(defaults, list) {
  if (!Array.isArray(list)) return defaults
  const known = new Set(defaults)
  const seen = new Set()
  const out = []
  for (const it of list) {
    if (!it || !known.has(it.id) || seen.has(it.id)) continue
    seen.add(it.id)
    if (it.visible !== false) out.push(it.id)
  }
  for (const id of defaults) if (!seen.has(id)) out.push(id)
  return out
}

// Fetched once per mount; never blocks the report - defaults render first, re-order on arrival.
export function useReportLayout() {
  const [orders, setOrders] = useState(DEFAULT_REPORT_ORDER)
  useEffect(() => {
    let cancelled = false
    fetchReportLayout().then(l => {
      if (cancelled || !l) return
      setOrders({
        summary: resolveOrder(DEFAULT_REPORT_ORDER.summary, l.summary),
        full: resolveOrder(DEFAULT_REPORT_ORDER.full, l.full),
      })
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])
  return orders
}
