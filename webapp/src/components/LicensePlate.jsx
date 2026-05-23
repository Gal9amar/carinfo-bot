function formatPlate(plate) {
  const digits = String(plate).replace(/\D/g, '')
  if (digits.length >= 8) {
    return `${digits.slice(0, 3)}·${digits.slice(3, 5)}·${digits.slice(5, 8)}`
  }
  if (digits.length === 7) {
    return `${digits.slice(0, 2)}-${digits.slice(2, 5)}-${digits.slice(5, 7)}`
  }
  return plate
}

export default function LicensePlate({ plate, size = 'md' }) {
  const formatted = formatPlate(plate)
  const lg = size === 'lg'

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'stretch',
      borderRadius: lg ? 10 : 7,
      border: `${lg ? 3 : 2}px solid #1a3896`,
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.22)',
      height: lg ? 64 : 46,
      direction: 'ltr',
    }}>
      {/* Blue IL section */}
      <div style={{
        background: 'linear-gradient(170deg, #1e40af 0%, #1230a0 100%)',
        color: '#fff',
        padding: lg ? '4px 8px' : '3px 6px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
        minWidth: lg ? 44 : 34,
      }}>
        <span style={{ fontSize: lg ? 20 : 15, lineHeight: 1 }}>🇮🇱</span>
        <span style={{
          fontSize: lg ? 11 : 8,
          fontWeight: 800,
          letterSpacing: 1,
          lineHeight: 1,
        }}>IL</span>
        <span style={{
          fontSize: lg ? 8 : 6,
          letterSpacing: 0.3,
          lineHeight: 1,
          opacity: 0.9,
        }}>ישראל</span>
      </div>

      {/* Yellow number section */}
      <div style={{
        background: '#FFE500',
        padding: lg ? '0 20px' : '0 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: '"Arial Black", "Arial Bold", Arial, sans-serif',
        fontWeight: 900,
        fontSize: lg ? 32 : 22,
        color: '#111',
        letterSpacing: lg ? 2 : 1.5,
        whiteSpace: 'nowrap',
      }}>
        {formatted}
      </div>
    </div>
  )
}
