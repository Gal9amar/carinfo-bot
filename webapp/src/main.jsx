import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

// Expand Telegram WebApp to full height
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.expand()
  window.Telegram.WebApp.ready()
}

// Prevent the mouse wheel from changing a focused number input's value —
// browsers do this by default, which silently corrupts values while
// scrolling a page past a numeric field.
document.addEventListener(
  'wheel',
  (e) => {
    if (document.activeElement?.tagName === 'INPUT' && document.activeElement.type === 'number') {
      document.activeElement.blur()
    }
  },
  { passive: true },
)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
