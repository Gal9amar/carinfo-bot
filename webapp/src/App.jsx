import { useState, useEffect } from 'react'
import { fetchPackages, fetchUser } from './api.js'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentPage from './pages/PaymentPage.jsx'
import AdminPage from './pages/AdminPage.jsx'
import ReportPage from './pages/ReportPage.jsx'

export default function App() {
  const [screen, setScreen] = useState('loading')
  const [packages, setPackages] = useState([])
  const [user, setUser] = useState(null)
  const [selectedPkg, setSelectedPkg] = useState(null)
  const [paymentData, setPaymentData] = useState(null)
  const [error, setError] = useState(null)
  const [reportPlate, setReportPlate] = useState(null)

  useEffect(() => {
    // Check if we're in vehicle report mode
    const params = new URLSearchParams(window.location.search)
    const plate = params.get('plate')
    if (plate) {
      setReportPlate(plate)
      setScreen('report')
      return
    }

    async function init() {
      try {
        const [pkgs, usr] = await Promise.all([fetchPackages(), fetchUser().catch(() => null)])
        setPackages(pkgs)
        setUser(usr)
        if (usr?.is_admin) {
          setScreen('admin')
        } else {
          setScreen('packages')
        }
      } catch (e) {
        setError('שגיאה בטעינה. נסה שוב.')
        setScreen('error')
      }
    }
    init()
  }, [])

  if (screen === 'report') {
    return <ReportPage plate={reportPlate} />
  }

  if (screen === 'loading') {
    return <div className="loading">⏳ טוען...</div>
  }

  if (screen === 'error') {
    return (
      <div className="page">
        <div className="loading">❌ {error}</div>
      </div>
    )
  }

  if (screen === 'admin') {
    return <AdminPage user={user} onBack={() => setScreen('packages')} />
  }

  if (screen === 'payment') {
    return (
      <PaymentPage
        pkg={selectedPkg}
        paymentData={paymentData}
        onBack={() => setScreen('packages')}
        onDone={() => setScreen('success')}
      />
    )
  }

  if (screen === 'success') {
    return (
      <div className="page">
        <div className="success-icon">✅</div>
        <div className="success-title">הבקשה נשלחה!</div>
        <div className="success-text">
          המנהל יאשר את התשלום בקרוב ותקבל הודעה בטלגרם.
        </div>
        <button className="btn" onClick={() => window.Telegram?.WebApp?.close()}>
          סגור
        </button>
      </div>
    )
  }

  return (
    <PackagesPage
      packages={packages}
      user={user}
      onSelect={(pkg, pData) => {
        setSelectedPkg(pkg)
        setPaymentData(pData)
        setScreen('payment')
      }}
    />
  )
}
