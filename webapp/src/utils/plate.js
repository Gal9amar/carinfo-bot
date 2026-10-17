// Plate as typed: 7 digits -> 12-345-67, 8 digits -> 123-45-678 (same as HomePage)
export function formatPlateInput(raw) {
  const d = String(raw || '').replace(/\D/g, '').slice(0, 8)
  if (d.length <= 2) return d
  if (d.length <= 5) return `${d.slice(0, 2)}-${d.slice(2)}`
  if (d.length === 8) return `${d.slice(0, 3)}-${d.slice(3, 5)}-${d.slice(5)}`
  return `${d.slice(0, 2)}-${d.slice(2, 5)}-${d.slice(5)}`
}
