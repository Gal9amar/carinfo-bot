// Renders admin-authored product descriptions with a small, safe tag
// allow-list (b/i/u/br) plus newline-to-<br> conversion — everything else is
// escaped as plain text. Not a general-purpose sanitizer: only call this on
// content that's already admin-only input (see ProductModal in AdminPage.jsx).
const ALLOWED_TAGS = new Set(['b', 'i', 'u', 'br'])

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function safeDescriptionHtml(text) {
  if (!text) return ''
  // Escape everything first, then re-open the small set of allowed tags —
  // this guarantees anything not in ALLOWED_TAGS stays inert text.
  const escaped = escapeHtml(text)
  const withTags = escaped.replace(
    /&lt;(\/?)(\w+)\s*&gt;/g,
    (match, closing, tag) => (ALLOWED_TAGS.has(tag.toLowerCase()) ? `<${closing}${tag.toLowerCase()}>` : match),
  )
  return withTags.replace(/\n/g, '<br>')
}
