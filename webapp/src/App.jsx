import { useState, useEffect, lazy, Suspense } from 'react'
import { fetchPackages, fetchUser, fetchVersion } from './api.js'
import HomePage from './pages/HomePage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'

// Heavy / rarely-used screens are code-split so the first paint only ships
// Home + the shared shell. Every page below has a default export.
const loaders = {
  report: () => import('./pages/ReportPage.jsx'),
  packages: () => import('./pages/PackagesPage.jsx'),
  payment: () => import('./pages/PaymentPage.jsx'),
  privacy: () => import('./pages/PrivacyPolicyPage.jsx'),
  ticket: () => import('./pages/TicketPage.jsx'),
  howItWorks: () => import('./pages/HowItWorksPage.jsx'),
  referral: () => import('./pages/ReferralPage.jsx'),
  watches: () => import('./pages/WatchesPage.jsx'),
  garage: () => import('./pages/GaragePage.jsx'),
  garageHowItWorks: () => import('./pages/GarageHowItWorksPage.jsx'),
  accessibility: () => import('./pages/AccessibilityPage.jsx'),
}
const AdminPage = lazy(() => import('./pages/AdminPage.jsx'))
const ReportPage = lazy(loaders.report)
const PackagesPage = lazy(loaders.packages)
const PaymentPage = lazy(loaders.payment)
const PrivacyPolicyPage = lazy(loaders.privacy)
const AccessibilityPage = lazy(loaders.accessibility)
const TicketPage = lazy(loaders.ticket)
const HowItWorksPage = lazy(loaders.howItWorks)
const ReferralPage = lazy(loaders.referral)
const WatchesPage = lazy(loaders.watches)
const GaragePage = lazy(loaders.garage)
const GarageHowItWorksPage = lazy(loaders.garageHowItWorks)

import BottomNav from './components/BottomNav.jsx'

function AppInner() {
  const [screen, setScreen] = useState('loading')
  const [screenStack, setScreenStack] = useState([])
  const [packages, setPackages] = useState([])
  const [user, setUser] = useState(null)
  const [loadError, setLoadError] = useState(false)
  const [selectedPkg, setSelectedPkg] = useState(null)
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
    if (page === 'accessibility') { setScreen('accessibility'); return }
    if (page === 'howItWorks') { setScreen('howItWorks'); return }
    if (page === 'history') { setScreen('history'); return }
    if (page === 'ticket') { setScreen('ticket'); return }
    if (page === 'referral') { setScreen('referral'); return }
    if (page === 'garage') { setScreen('garage'); return }
    if (page === 'watches') {
      setScreen('watches')
      fetchUser().catch(() => null).then(usr => setUser(usr))
      fetchPackages().then(setPackages).catch(() => {})
      return
    }
    if (page === 'garageHowItWorks') { setScreen('garageHowItWorks'); return }
    if (page === 'profile') {
      setScreen('profile')
      fetchUser().catch(() => null).then(usr => setUser(usr))
      return
    }

    if (page) { setScreen('notFound'); return }   // unknown ?page=… deep link

    // Show Home immediately; user and packages load in parallel and fill in
    // as they arrive (neither blocks first paint).
    setScreen('home')
    loadHome()
  }, [])

  function loadHome() {
    setLoadError(false)
    fetchUser().then(setUser).catch(() => setLoadError(true))
    fetchPackages().then(setPackages).catch(() => {})
  }

  // After first paint, warm the chunks users most often open next.
  useEffect(() => {
    const warm = () => { loaders.report(); loaders.packages() }
    const id = window.requestIdleCallback ? window.requestIdleCallback(warm, { timeout: 4000 }) : setTimeout(warm, 2000)
    return () => { window.cancelIdleCallback ? window.cancelIdleCallback(id) : clearTimeout(id) }
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
    const first = setTimeout(checkVersion, 3000) // don't compete with boot requests
    const interval = setInterval(checkVersion, 5 * 60 * 1000)
    return () => { clearTimeout(first); clearInterval(interval) }
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
    if (screen === 'home' || screen === 'loading' || screen === 'notFound') {
      tg.BackButton.hide()
    } else {
      tg.BackButton.show()
    }
    tg.BackButton.onClick(goBack)
    return () => tg.BackButton.offClick(goBack)
  }, [screen, screenStack])

  if (user?.consent_required && !['privacy', 'accessibility', 'howItWorks'].includes(screen)) {
    const tg = window.Telegram?.WebApp
    const open = () => {
      const url = `https://t.me/${user.bot_username || 'israelcarinfobot'}?start=welcome`
      if (tg?.openTelegramLink) { tg.openTelegramLink(url); tg.close?.() } else { window.location.href = url }
    }
    return (
      <div className="page">
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 44 }}>👋</div>
          <div style={{ fontWeight: 800, fontSize: 17, margin: '6px 0' }}>כדי להשתמש בשירות יש להפעיל את הבוט</div>
          <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-muted)', marginBottom: 14 }}>
            הפעלת הבוט מהווה הסכמה לתנאי השימוש, למדיניות הפרטיות ולקבלת הודעות מהשירות.
          </div>
          <button className="btn" style={{ marginTop: 0 }} onClick={open}>▶️ הפעל את הבוט</button>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 12 }}>
            <button onClick={() => navigate('privacy')} style={{ background: 'none', border: 'none', textDecoration: 'underline', color: 'var(--text-muted)', fontSize: 13, cursor: 'pointer' }}>מדיניות פרטיות</button>
          </div>
        </div>
      </div>
    )
  }

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
        <PrivacyPolicyPage onBack={goBack} onContact={() => navigate('ticket')} onNavigate={navigate} onAccessibility={() => navigate('accessibility')} />
      </div>
    )
  }

  if (screen === 'accessibility') {
    return (
      <div key="accessibility" className="page-enter">
        <AccessibilityPage onBack={goBack} onContact={() => navigate('ticket')} />
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

  if (screen === 'profile') {
    return (
      <>
        <div key="profile" className="page-enter" style={{ paddingBottom: 78 }}>
          <ProfilePage user={user} onBack={goBack} onNavigate={navigate}
            onAccountDeleted={() => { setScreenStack([]); setUser({ consent_required: true, bot_username: user?.bot_username }); setScreen('home') }} />
        </div>
        <BottomNav screen={screen} onNavigate={navigate} />
      </>
    )
  }

  if (screen === 'garageHowItWorks') {
    return (
      <div key="garageHowItWorks" className="page-enter">
        <GarageHowItWorksPage onBack={goBack} onNavigate={navigate} />
      </div>
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

  if (screen === 'notFound') {
    return (
      <div className="page">
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48 }}>🚗</div>
          <div style={{ fontSize: 48, fontWeight: 800 }}>404</div>
          <div style={{ margin: '8px 0 16px' }}>הדף שחיפשת לא נמצא</div>
          <button className="btn" style={{ marginTop: 0 }} onClick={() => {
            window.history.replaceState(null, '', window.location.pathname)
            setScreen('home')
            loadHome()
          }}>חזרה לדף הבית</button>
        </div>
      </div>
    )
  }

  if (screen === 'loading') {
    return <HomeSkeleton />
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
          <div style={{
            width: 88, height: 88, borderRadius: '50%', margin: '56px auto 18px',
            background: 'rgba(52, 199, 89, 0.15)', color: '#1b8a3a',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 44,
          }}>✓</div>
          <div className="success-title">הבקשה נשלחה!</div>
          <div className="success-text">
            נאשר את הרכישה בקרוב ותקבל הודעה בטלגרם.
          </div>
          <button className="btn" onClick={() => { setScreenStack([]); setScreen('home') }}>
            חזרה לבית
          </button>
          <button className="btn btn-outline" onClick={() => navigate('orders')}>
            ההזמנות שלי
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

  if (screen === 'home' && loadError && !user) {
    return (
      <div className="page">
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 40 }}>⚠️</div>
          <div style={{ margin: '8px 0 16px' }}>לא הצלחנו לטעון את הנתונים. בדוק את החיבור ונסה שוב</div>
          <button className="btn" style={{ marginTop: 0 }} onClick={loadHome}>🔄 נסה שוב</button>
        </div>
      </div>
    )
  }

  // Default: home screen for regular users
  return (
    <>
      <div key="home" className="page-enter" style={{ paddingBottom: 78 }}>
        <HomePage
          user={user}
          onNavigate={navigate}
          onSearchPlate={(plate) => {
            setReportPlate(plate)
            navigate('report')
          }}
        />
      </div>
      <BottomNav screen="home" onNavigate={navigate} />
    </>
  )
}

function HomeSkeleton() {
  return (
    <div className="page" aria-busy="true">
      <div className="skeleton" style={{ height: 120, borderRadius: 20, marginBottom: 16 }} />
      <div className="skeleton" style={{ height: 64, borderRadius: 20, marginBottom: 16 }} />
      <div className="skeleton" style={{ height: 160, borderRadius: 20 }} />
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<HomeSkeleton />}>
      <AppInner />
    </Suspense>
  )
}
