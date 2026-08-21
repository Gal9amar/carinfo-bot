// Shared Yad2 market-price stats — used by ReportPage and GaragePage so the
// median/min/max calculation stays in one place instead of drifting between
// copies.

function median(sortedPrices) {
  return sortedPrices[Math.floor(sortedPrices.length / 2)]
}

// Returns { median } or null if there's no usable market data.
export function getMarketMedian(marketData, year) {
  const stats = getMarketStats(marketData, year)
  return stats ? stats.median : null
}

// Returns { prices, median, min, max, avgKm } or null if there's no usable market data.
export function getMarketStats(marketData, year) {
  if (!marketData?.market) return null
  const m = marketData.market
  const yr = year ? parseInt(year) : null
  const filtered = yr && m.items?.length
    ? m.items.filter(i => parseInt(i.vehicleDates?.yearOfProduction || 0) === yr)
    : m.items || []
  const pool = filtered.length > 0 ? filtered : m.items || []
  const prices = pool.map(i => i.price).filter(Boolean).sort((a, b) => a - b)
  if (!prices.length) return null
  const kms = pool.map(i => i.km).filter(Boolean)
  return {
    prices,
    median: median(prices),
    min: prices[0],
    max: prices[prices.length - 1],
    avgKm: kms.length ? Math.round(kms.reduce((a, b) => a + b, 0) / kms.length) : null,
  }
}
