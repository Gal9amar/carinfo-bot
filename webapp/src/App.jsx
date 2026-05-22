import { useState, useEffect } from 'react'
import { fetchPackages, fetchUser } from './api.js'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentPage from './pages/PaymentPage.jsx'
import AdminPage from './pages/AdminPage.jsx'
import ReportPage from './pages/ReportPage.jsx'
import PrivacyPolicyPage from './pages/PrivacyPolicyPage.jsx'
import TicketPage from './pages/TicketPage.jsx'
import HowItWorksPage from './pages/HowItWorksPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import ReferralPage from './pages/ReferralPage.jsx'

export default function App() {
  const [screen, setScreen] = useState('loading')
  const [packages, setPackages] = useState([])
  const [user, setUser] = useState(null)
  const [selectedPkg, setSelectedPkg] = useState(null)
  const [paymentData, setPaymentData] = useState(null)
  const [error, setError] = useState(null)
  const [reportPlate, setReportPlate] = useState(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const plate = params.get('plate')
    const page = params.get('page')
    if (plate) {
      setReportPlate(plate)
      setScreen('report')
      return
    }
    if (page === 'privacy') { setScreen('privacy'); return }
    if (page === 'howItWorks') { setScreen('howItWorks'); return }
    if (page === 'history') { setScreen('history'); return }
    if (page === 'ticket') { setScreen('ticket'); return }
    if (page === 'referral') { setScreen('referral'); return }

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

  if (screen === 'privacy') {
    return <PrivacyPolicyPage onBack={() => setScreen('packages')} onContact={() => setScreen('ticket')} />
  }

  if (screen === 'ticket') {
    return <TicketPage onBack={() => setScreen('packages')} />
  }

  if (screen === 'howItWorks') {
    return <HowItWorksPage onBack={() => setScreen('packages')} freeSearches={user?.free_searches ?? 10} />
  }

  if (screen === 'history') {
    return (
      <HistoryPage
        onBack={() => setScreen('packages')}
        onViewPlate={plate => { setReportPlate(plate); setScreen('report') }}
      />
    )
  }

  if (screen === 'referral') {
    return <ReferralPage onBack={() => setScreen('packages')} />
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
      onPrivacy={() => setScreen('privacy')}
      onSupport={() => setScreen('ticket')}
      onReferral={() => setScreen('referral')}
    />
  )
}
