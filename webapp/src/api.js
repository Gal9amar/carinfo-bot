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

export async function initiatePayment(packageId) {
  const r = await fetch(`${BASE}/api/payment/initiate`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ package_id: packageId }),
  })
  if (!r.ok) throw new Error('Payment init failed')
  return r.json()
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
  const r = await fetch(`${BASE}/api/vehicle/${plate}`, { headers: headers() })
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

export async function adminGrantUser(userId, searches) {
  const r = await fetch(`${BASE}/api/admin/users/${userId}/grant`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ searches }),
  })
  if (!r.ok) throw new Error('Failed')
  return r.json()
}
