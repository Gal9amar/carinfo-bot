const BASE = ''

function headers() {
  const initData = window.Telegram?.WebApp?.initData || ''
  return {
    'Content-Type': 'application/json',
    'X-Init-Data': initData,
  }
}

export async function fetchPackages() {
  const r = await fetch(`${BASE}/api/packages`)
  if (!r.ok) throw new Error('Failed to load packages')
  return r.json()
}

export async function fetchUser() {
  const r = await fetch(`${BASE}/api/user`, { headers: headers() })
  if (!r.ok) throw new Error('Auth failed')
  return r.json()
}

export async function fetchUserOrders() {
  const r = await fetch(`${BASE}/api/user/orders`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function initiatePayment(packageId, quantity = 1, intentOnly = false) {
  const r = await fetch(`${BASE}/api/payment/initiate`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ package_id: packageId, quantity, intent_only: intentOnly }),
  })
  if (!r.ok) throw new Error('Payment init failed')
  return r.json()
}

export function promotePayment(ref) {
  fetch(`${BASE}/api/payment/promote`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ ref }),
  }).catch(() => {})
}

export async function confirmPayment(ref, packageId) {
  const r = await fetch(`${BASE}/api/payment/confirm`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ ref, package_id: packageId }),
  })
  if (!r.ok) throw new Error('Confirm failed')
  return r.json()
}

export async function fetchVehicle(plate) {
  const r = await fetch(`${BASE}/api/vehicle/${plate}`, { headers: headers(), cache: 'no-store' })
  if (!r.ok) throw new Error('Vehicle not found')
  return r.json()
}

// Admin
export async function adminFetchStats() {
  const r = await fetch(`${BASE}/api/admin/stats`, { headers: headers() })
  if (!r.ok) throw new Error('Unauthorized')
  return r.json()
}

export async function adminFetchUsers() {
  const r = await fetch(`${BASE}/api/admin/users`, { headers: headers() })
  if (!r.ok) throw new Error('Unauthorized')
  return r.json()
}

export async function adminFetchSettings() {
  const r = await fetch(`${BASE}/api/admin/settings`, { headers: headers() })
  if (!r.ok) throw new Error('Unauthorized')
  return r.json()
}

export async function adminUpdateSettings(data) {
  const r = await fetch(`${BASE}/api/admin/settings`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Update failed')
  return r.json()
}

export async function adminFetchPackages() {
  const r = await fetch(`${BASE}/api/admin/packages`, { headers: headers() })
  if (!r.ok) throw new Error('Unauthorized')
  return r.json()
}

export async function adminAddPackage(data) {
  const r = await fetch(`${BASE}/api/admin/packages`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminUpdatePackage(id, data) {
  const r = await fetch(`${BASE}/api/admin/packages/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminDeletePackage(id) {
  const r = await fetch(`${BASE}/api/admin/packages/${id}`, {
    method: 'DELETE',
    headers: headers(),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminReorderPackages(order) {
  const r = await fetch(`${BASE}/api/admin/packages/reorder`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify({ order }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminFetchGrants() {
  const r = await fetch(`${BASE}/api/admin/grants`, { headers: headers() })
  if (!r.ok) throw new Error('Unauthorized')
  return r.json()
}

export async function adminAddGrant(data) {
  const r = await fetch(`${BASE}/api/admin/grants`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminUpdateGrant(id, data) {
  const r = await fetch(`${BASE}/api/admin/grants/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminDeleteGrant(id) {
  const r = await fetch(`${BASE}/api/admin/grants/${id}`, {
    method: 'DELETE',
    headers: headers(),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminReorderGrants(order) {
  const r = await fetch(`${BASE}/api/admin/grants/reorder`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify({ order }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminRevokeSubscription(userId) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/revoke-subscription`, {
    method: 'POST',
    headers: headers(),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminGrantUser(userId, searches) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/grant`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ searches }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminSetWatchQuota(userId, watchQuota) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/watch-quota`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ watch_quota: watchQuota }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function fetchSearchHistory() {
  const r = await fetch(`${BASE}/api/user/history`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Tickets (user)
export async function createTicket(subject, message) {
  const r = await fetch(`${BASE}/api/tickets`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ subject, message }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function fetchMyTickets() {
  const r = await fetch(`${BASE}/api/tickets`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function fetchTicket(id) {
  const r = await fetch(`${BASE}/api/tickets/${id}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function replyTicket(id, message) {
  const r = await fetch(`${BASE}/api/tickets/${id}/reply`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Tickets (admin)
export async function adminFetchTickets(status) {
  const url = status ? `${BASE}/api/admin/tickets?status=${status}` : `${BASE}/api/admin/tickets`
  const r = await fetch(url, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminFetchTicket(id) {
  const r = await fetch(`${BASE}/api/admin/tickets/${id}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminReplyTicket(id, message) {
  const r = await fetch(`${BASE}/api/admin/tickets/${id}/reply`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminUpdateTicketStatus(id, status) {
  const r = await fetch(`${BASE}/api/admin/tickets/${id}/status`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify({ status }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// PayPal transactions admin
export async function adminFetchPaypalTransactions() {
  const r = await fetch(`${BASE}/api/admin/paypal/transactions`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Payments admin
export async function adminFetchPayments() {
  const r = await fetch(`${BASE}/api/admin/payments`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminApprovePayment(ref) {
  const r = await fetch(`${BASE}/api/admin/payments/${ref}/approve`, { method: 'POST', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminDeclinePayment(ref) {
  const r = await fetch(`${BASE}/api/admin/payments/${ref}/decline`, { method: 'POST', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminOrderApprove(ref) {
  const r = await fetch(`${BASE}/api/admin/orders/${ref}/approve`, { method: 'POST', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminOrderCancel(ref) {
  const r = await fetch(`${BASE}/api/admin/orders/${ref}/cancel`, { method: 'POST', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Codes admin
export async function adminFetchCodes() {
  const r = await fetch(`${BASE}/api/admin/codes`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminCreateCode(data) {
  const r = await fetch(`${BASE}/api/admin/codes`, {
    method: 'POST', headers: headers(), body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminDeleteCode(code) {
  const r = await fetch(`${BASE}/api/admin/codes/${code}`, { method: 'DELETE', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Broadcast
export async function adminFetchBroadcastHistory() {
  const r = await fetch(`${BASE}/api/admin/broadcast/history`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminBroadcast(message, image_b64 = '') {
  const r = await fetch(`${BASE}/api/admin/broadcast`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ message, image_b64 }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Block/unblock
export async function adminToggleBlock(userId) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/block`, { method: 'POST', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Direct message to user
export async function adminSendUserMessage(userId, message) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/message`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// User referral history (admin view)
export async function adminFetchUserReferrals(userId) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/referrals`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// User search history (admin view)
export async function adminFetchUserHistory(userId) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/history`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// System messages sent to user (admin view)
export async function adminFetchUserSentMessages(userId) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/sent-messages`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Referral info for current user
export async function fetchReferral() {
  const r = await fetch(`${BASE}/api/user/referral`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// List of users referred by current user
export async function fetchReferrals() {
  const r = await fetch(`${BASE}/api/user/referrals`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Gift searches to all users
export async function adminGiftAll(searches, message, image_b64 = '', gift_type = 'searches') {
  const r = await fetch(`${BASE}/api/admin/gift-all`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ searches, message, image_b64, gift_type }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Activity log
export async function adminFetchActivity(limit = 100) {
  const r = await fetch(`${BASE}/api/admin/activity?limit=${limit}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Market price (user)
export async function fetchMarketPrice(plate) {
  const r = await fetch(`${BASE}/api/vehicle/${encodeURIComponent(plate)}/market-price`, { headers: headers() })
  if (!r.ok) return null
  return r.json()
}

export async function fetchNote(plate) {
  const r = await fetch(`${BASE}/api/notes/${encodeURIComponent(plate)}`, { headers: headers() })
  if (!r.ok) return ''
  const d = await r.json()
  return d.note || ''
}

export async function saveNote(plate, note) {
  await fetch(`${BASE}/api/notes/${encodeURIComponent(plate)}`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ note }),
  })
}

export async function requestPdfReport(plate) {
  const r = await fetch(`${BASE}/api/vehicle/${encodeURIComponent(plate)}/pdf`, { headers: headers() })
  if (!r.ok) throw new Error('PDF not available')
  return r.json()
}

// Groups admin
export async function adminFetchGroups() {
  const r = await fetch(`${BASE}/api/admin/groups`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminCreateGroup(name) {
  const r = await fetch(`${BASE}/api/admin/groups`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ name }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminDeleteGroup(id) {
  const r = await fetch(`${BASE}/api/admin/groups/${id}`, {
    method: 'DELETE', headers: headers(),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminAddGroupMember(groupId, userId) {
  const r = await fetch(`${BASE}/api/admin/groups/${groupId}/members`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ user_id: userId }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function adminRemoveGroupMember(groupId, userId) {
  const r = await fetch(`${BASE}/api/admin/groups/${groupId}/members/${userId}`, {
    method: 'DELETE', headers: headers(),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Market price (admin)
export async function adminFetchMarketPrice(plate) {
  const r = await fetch(`${BASE}/api/admin/market-price?plate=${encodeURIComponent(plate)}`, { headers: headers() })
  if (r.status === 404) throw new Error('רכב לא נמצא')
  if (!r.ok) throw new Error('שגיאה בשליפה')
  return r.json()
}

// Yad2 Watch reference data
export async function fetchWatchMakes() {
  const r = await fetch(`${BASE}/api/watches/makes`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function fetchWatchModels(make) {
  const r = await fetch(`${BASE}/api/watches/models?make=${encodeURIComponent(make)}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Yad2 Watches (user)
export async function fetchUserWatches() {
  const r = await fetch(`${BASE}/api/user/watches`, { headers: headers() })
  if (r.status === 403) throw new Error('FORBIDDEN')
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function createUserWatch(data) {
  const r = await fetch(`${BASE}/api/user/watches`, {
    method: 'POST', headers: headers(), body: JSON.stringify(data),
  })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Failed') }
  return r.json()
}
export async function deleteUserWatch(id) {
  const r = await fetch(`${BASE}/api/user/watches/${id}`, { method: 'DELETE', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function toggleUserWatch(id) {
  const r = await fetch(`${BASE}/api/user/watches/${id}/toggle`, { method: 'PATCH', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

// Yad2 Watches (admin)
export async function adminFetchWatches() {
  const r = await fetch(`${BASE}/api/admin/watches`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminCreateWatch(data) {
  const r = await fetch(`${BASE}/api/admin/watches`, {
    method: 'POST', headers: headers(), body: JSON.stringify(data),
  })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Failed') }
  return r.json()
}
export async function adminDeleteWatch(id) {
  const r = await fetch(`${BASE}/api/admin/watches/${id}`, { method: 'DELETE', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminToggleWatch(id) {
  const r = await fetch(`${BASE}/api/admin/watches/${id}/toggle`, { method: 'PATCH', headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminWatchMakes() {
  const r = await fetch(`${BASE}/api/admin/watches/makes`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminWatchModels(make) {
  const r = await fetch(`${BASE}/api/admin/watches/models?make=${encodeURIComponent(make)}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
export async function adminWatchPreview(make, model, year) {
  let url = `${BASE}/api/admin/watches/preview?make=${encodeURIComponent(make)}`
  if (model) url += `&model=${encodeURIComponent(model)}`
  if (year)  url += `&year=${year}`
  const r = await fetch(url, { headers: headers() })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
