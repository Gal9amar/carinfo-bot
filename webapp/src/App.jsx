import { useState, useEffect, lazy, Suspense } from 'react'
import { fetchPackages, fetchUser, fetchVersion } from './api.js'
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
import WatchesPage from './pages/WatchesPage.jsx'
import GaragePage from './pages/GaragePage.jsx'
import BottomNav from './components/BottomNav.jsx'

export default function App() {
  const [screen, setScreen] = useState('loading')
  const [screenStack, setScreenStack] = useState([])
  const [packages, setPackages] = useState([])
  const [user, setUser] = useState(null)
  const [selectedPkg, setSelectedPkg] = useState(null)
  const [paymentData, setPaymentData] = useState(null)
  const [error, setError] = useState(null)
  const [reportPlate, setReportPlate] = useState(null)
  const [highlightProductId, setHighlightProductId] = useState(null)

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
    if (page === 'garage') { setScreen('garage'); return }

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

  // Detect a new deploy and force a fresh reload instead of running on a
  // stale cached build. Runs on mount and then periodically, so it also
  // catches a deploy that happens while the mini app is left open.
  useEffect(() => {
    const VERSION_KEY = 'app_version'
    async function checkVersion() {
      try {
        const { version } = await fetchVersion()
        const stored = localStorage.getItem(VERSION_KEY)
        if (!stored) {
          localStorage.setItem(VERSION_KEY, version)
        } else if (stored !== version) {
          localStorage.setItem(VERSION_KEY, version)
          window.location.reload()
        }
      } catch { /* offline or version endpoint unreachable — ignore */ }
    }
    checkVersion()
    const interval = setInterval(checkVersion, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  // Push the current screen onto the stack, then move to `dest`.
  function navigate(dest, meta) {
    setHighlightProductId(meta?.highlightProductId ?? null)
    setScreenStack(s => [...s, screen])
    setScreen(dest)
  }

  // Pop the previous screen off the stack — used by both the in-page back
  // arrows and the phone/Telegram hardware back button, so both agree on
  // where "back" leads.
  function goBack() {
    setScreenStack(s => {
      if (s.length === 0) { setScreen('home'); return s }
      setScreen(s[s.length - 1])
      return s.slice(0, -1)
    })
  }

  // Telegram's native back button (and the phone's hardware/gesture back,
  // which Telegram routes to it) should navigate within the mini app
  // instead of closing it.
  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (!tg?.BackButton) return
    if (screen === 'home' || screen === 'loading' || screen === 'error') {
      tg.BackButton.hide()
    } else {
      tg.BackButton.show()
    }
    tg.BackButton.onClick(goBack)
    return () => tg.BackButton.offClick(goBack)
  }, [screen, screenStack])

  if (screen === 'report') {
    return (
      <div key="report" className="page-enter">
        <ReportPage
          plate={reportPlate}
          onBack={(dest) => dest ? navigate(dest) : goBack()}
          user={user}
          onNavigate={navigate}
        />
      </div>
    )
  }

  if (screen === 'privacy') {
    return (
      <div key="privacy" className="page-enter">
        <PrivacyPolicyPage onBack={goBack} onContact={() => navigate('ticket')} onNavigate={navigate} />
      </div>
    )
  }

  if (screen === 'ticket') {
    return (
      <>
        <div key="ticket" className="page-enter" style={{ paddingBottom: 78 }}>
          <TicketPage onBack={goBack} onNavigate={navigate} />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'howItWorks') {
    return (
      <div key="howItWorks" className="page-enter">
        <HowItWorksPage onBack={goBack} freeSearches={user?.free_searches ?? 10} onPrivacy={() => navigate('privacy')} onNavigate={navigate} />
      </div>
    )
  }

  if (screen === 'history') {
    return (
      <>
        <div key="history" className="page-enter" style={{ paddingBottom: 78 }}>
          <HistoryPage
            onBack={goBack}
            onViewPlate={plate => { setReportPlate(plate); navigate('report') }}
            onNavigate={navigate}
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
          <ReferralPage onBack={goBack} onNavigate={navigate} />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'garage') {
    return (
      <>
        <div key="garage" className="page-enter" style={{ paddingBottom: 78 }}>
          <GaragePage onBack={goBack} onNavigate={navigate} />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'orders') {
    return (
      <div key="orders" className="page-enter">
        <OrdersPage onBack={goBack} onNavigate={navigate} />
      </div>
    )
  }

  if (screen === 'watches') {
    return (
      <div key="watches" className="page-enter">
        <WatchesPage onBack={goBack} onPackages={() => navigate('packages')} user={user} onNavigate={navigate} />
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
          <AdminPage user={user} onBack={goBack} />
        </Suspense>
      </div>
    )
  }

  if (screen === 'payment') {
    return (
      <div key="payment" className="page-enter">
        <PaymentPage
          pkg={selectedPkg}
          onBack={goBack}
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
            נאשר את הרכישה בקרוב ותקבל הודעה בטלגרם.
          </div>
          <button className="btn" onClick={() => { setScreenStack([]); setScreen('home') }}>
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
            highlightProductId={highlightProductId}
            onSelect={(pkg) => {
              setSelectedPkg(pkg)
              setPaymentData(null)
              navigate('payment')
            }}
            onPrivacy={() => navigate('privacy')}
            onSupport={() => navigate('ticket')}
            onReferral={() => navigate('referral')}
            onBack={goBack}
            onNavigate={navigate}
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
