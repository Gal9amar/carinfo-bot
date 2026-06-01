import { useState, useEffect, lazy, Suspense } from 'react'
import { fetchPackages, fetchUser } from './api.js'
import HomePage from './pages/HomePage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentPage from './pages/PaymentPage.jsx'
const AdminPage = lazy(() => import('./pages/AdminPage.jsx'))
import ReportPage from './pages/ReportPage.jsx'
import PrivacyPolicyPage from './pages/PrivacyPolicyPage.jsx'
import TicketPage from './pages/TicketPage.jsx'
import HowItWorksPage from './pages/HowItWorksPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import ReferralPage from './pages/ReferralPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import BottomNav from './components/BottomNav.jsx'

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
      fetchUser().catch(() => null).then(usr => setUser(usr))
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
        setScreen('home')
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

  if (screen === 'report') {
    return (
      <div key="report" className="page-enter">
        <ReportPage
          plate={reportPlate}
          onBack={(dest) => setScreen(dest ?? 'home')}
          user={user}
        />
      </div>
    )
  }

  if (screen === 'privacy') {
    return (
      <div key="privacy" className="page-enter">
        <PrivacyPolicyPage onBack={() => setScreen('home')} onContact={() => setScreen('ticket')} />
      </div>
    )
  }

  if (screen === 'ticket') {
    return (
      <>
        <div key="ticket" className="page-enter" style={{ paddingBottom: 78 }}>
          <TicketPage onBack={() => setScreen('home')} />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'howItWorks') {
    return (
      <div key="howItWorks" className="page-enter">
        <HowItWorksPage onBack={() => setScreen('home')} freeSearches={user?.free_searches ?? 10} onPrivacy={() => setScreen('privacy')} />
      </div>
    )
  }

  if (screen === 'history') {
    return (
      <>
        <div key="history" className="page-enter" style={{ paddingBottom: 78 }}>
          <HistoryPage
            onBack={() => setScreen('home')}
            onViewPlate={plate => { setReportPlate(plate); setScreen('report') }}
          />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'referral') {
    return (
      <>
        <div key="referral" className="page-enter" style={{ paddingBottom: 78 }}>
          <ReferralPage onBack={() => setScreen('home')} />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'orders') {
    return (
      <div key="orders" className="page-enter">
        <OrdersPage onBack={() => setScreen('home')} />
      </div>
    )
  }

  if (screen === 'loading') {
    return <div className="loading"></div>
  }

  if (screen === 'error') {
    return (
      <div className="page">
        <div className="loading">❌ {error}</div>
      </div>
    )
  }

  if (screen === 'admin') {
    return (
      <div key="admin" className="page-enter">
        <Suspense fallback={<div className="loading"></div>}>
          <AdminPage user={user} onBack={() => setScreen('home')} />
        </Suspense>
      </div>
    )
  }

  if (screen === 'payment') {
    return (
      <div key="payment" className="page-enter">
        <PaymentPage
          pkg={selectedPkg}
          onBack={() => setScreen('packages')}
        />
      </div>
    )
  }

  if (screen === 'success') {
    return (
      <div key="success" className="page-enter">
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
      </div>
    )
  }

  if (screen === 'packages') {
    return (
      <>
        <div key="packages" className="page-enter" style={{ paddingBottom: 78 }}>
          <PackagesPage
            packages={packages}
            user={user}
            onSelect={(pkg) => {
              setSelectedPkg(pkg)
              setPaymentData(null)
              setScreen('payment')
            }}
            onPrivacy={() => setScreen('privacy')}
            onSupport={() => setScreen('ticket')}
            onReferral={() => setScreen('referral')}
            onBack={() => setScreen('home')}
          />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  // Default: home screen for regular users
  return (
    <>
      <div key="home" className="page-enter" style={{ paddingBottom: 78 }}>
        <HomePage
          user={user}
          onNavigate={navigate}
        />
      </div>
      <BottomNav screen="home" onNavigate={navigate} />
    </>
  )
}
