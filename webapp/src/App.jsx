import { useState, useEffect } from 'react'
import { fetchPackages, fetchUser } from './api.js'
import HomePage from './pages/HomePage.jsx'
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
  const [reportDeduct, setReportDeduct] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const plate = params.get('plate')
    const page = params.get('page')
    if (plate) {
      setReportPlate(plate)
      setReportDeduct(false) // deep-link from bot = quota already deducted
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
          setScreen('home')
        }
      } catch (e) {
        setError('שגיאה בטעינה. נסה שוב.')
        setScreen('error')
      }
    }
    init()
  }, [])

  function navigate(dest) {
    setScreen(dest)
  }

  function openReport(plate) {
    setReportPlate(plate)
    setReportDeduct(true) // user-initiated search = deduct quota
    setScreen('report')
  }

  if (screen === 'report') {
    return (
      <ReportPage
        plate={reportPlate}
        deduct={reportDeduct}
        onBack={(dest) => setScreen(dest ?? 'home')}
      />
    )
  }

  if (screen === 'privacy') {
    return <PrivacyPolicyPage onBack={() => setScreen('home')} onContact={() => setScreen('ticket')} />
  }

  if (screen === 'ticket') {
    return <TicketPage onBack={() => setScreen('home')} />
  }

  if (screen === 'howItWorks') {
    return <HowItWorksPage onBack={() => setScreen('home')} freeSearches={user?.free_searches ?? 10} onPrivacy={() => setScreen('privacy')} />
  }

  if (screen === 'history') {
    return (
      <HistoryPage
        onBack={() => setScreen('home')}
        onViewPlate={plate => { setReportPlate(plate); setReportDeduct(false); setScreen('report') }}
      />
    )
  }

  if (screen === 'referral') {
    return <ReferralPage onBack={() => setScreen('home')} />
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
    return <AdminPage user={user} onBack={() => setScreen('home')} />
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
        <button className="btn" onClick={() => setScreen('home')}>
          חזור לתפריט
        </button>
      </div>
    )
  }

  if (screen === 'packages') {
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
        onBack={() => setScreen('home')}
      />
    )
  }

  // Default: home screen for regular users
  return (
    <HomePage
      user={user}
      onSearch={openReport}
      onNavigate={navigate}
    />
  )
}
