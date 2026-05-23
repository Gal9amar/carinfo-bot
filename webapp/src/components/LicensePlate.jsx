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

const SIZES = {
  sm: { h: 38, r: 6, bw: 2, flag: 12, il: 6,  isr: 5,  mw: 28, py: '3px 5px',  numSz: 17, numPx: '0 10px', ls: 1   },
  md: { h: 46, r: 7, bw: 2, flag: 15, il: 8,  isr: 6,  mw: 34, py: '3px 6px',  numSz: 22, numPx: '0 14px', ls: 1.5 },
  lg: { h: 64, r: 10, bw: 3, flag: 20, il: 11, isr: 8, mw: 44, py: '4px 8px',  numSz: 32, numPx: '0 20px', ls: 2   },
}

export default function LicensePlate({ plate, size = 'md' }) {
  const formatted = formatPlate(plate)
  const s = SIZES[size] || SIZES.md

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'stretch',
      borderRadius: s.r,
      border: `${s.bw}px solid #1a3896`,
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.22)',
      height: s.h,
      direction: 'ltr',
      flexShrink: 0,
    }}>
      {/* Blue IL section */}
      <div style={{
        background: 'linear-gradient(170deg, #1e40af 0%, #1230a0 100%)',
        color: '#fff',
        padding: s.py,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
        minWidth: s.mw,
      }}>
        <span style={{ fontSize: s.flag, lineHeight: 1 }}>🇮🇱</span>
        <span style={{ fontSize: s.il, fontWeight: 800, letterSpacing: 1, lineHeight: 1 }}>IL</span>
        <span style={{ fontSize: s.isr, letterSpacing: 0.3, lineHeight: 1, opacity: 0.9 }}>ישראל</span>
      </div>

      {/* Yellow number section */}
      <div style={{
        background: '#FFE500',
        padding: s.numPx,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: '"Arial Black", "Arial Bold", Arial, sans-serif',
        fontWeight: 900,
        fontSize: s.numSz,
        color: '#111',
        letterSpacing: s.ls,
        whiteSpace: 'nowrap',
      }}>
        {formatted}
      </div>
    </div>
  )
}
