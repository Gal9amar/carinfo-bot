export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': '*',
        },
      })
    }

    const url = new URL(request.url)
    const manufacturer = url.searchParams.get('manufacturer')
    const model        = url.searchParams.get('model')
    const year         = url.searchParams.get('year')
    const type         = url.searchParams.get('type') || 'lookalike'

    if (!manufacturer && !model) {
      return new Response(JSON.stringify({ error: 'missing manufacturer or model param' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      })
    }

    // type=feed  → full search results (all listings)
    // type=lookalike (default) → market price comparison sample (existing behaviour)
    // Note: Yad2's API rejects unrecognized params (e.g. `rows`) with a 400 — only send what it accepts.
    const endpoint = type === 'feed'
      ? 'https://gw.yad2.co.il/feed/vehicles/cars'
      : 'https://gw.yad2.co.il/lookalike/vehicles/cars'

    const yad2params = []
    if (model)        yad2params.push(`model=${model}`)
    else if (manufacturer) yad2params.push(`manufacturer=${manufacturer}`)
    if (year)         yad2params.push(`year=${year}`)
    let yad2url = `${endpoint}?${yad2params.join('&')}`

    let resp
    try {
      resp = await fetch(yad2url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
          'Referer': 'https://www.yad2.co.il/vehicles/cars',
          'Origin': 'https://www.yad2.co.il',
          'Sec-Fetch-Dest': 'empty',
          'Sec-Fetch-Mode': 'cors',
          'Sec-Fetch-Site': 'same-site',
        }
      })
    } catch (e) {
      return new Response(JSON.stringify({ error: 'fetch failed', detail: String(e) }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      })
    }

    // Decompress if needed
    let body = resp.body
    const encoding = resp.headers.get('content-encoding') || ''
    if (encoding.includes('gzip') || encoding.includes('br') || encoding.includes('deflate')) {
      const format = encoding.includes('br') ? 'deflate-raw' : encoding.includes('gzip') ? 'gzip' : 'deflate'
      try {
        body = body.pipeThrough(new DecompressionStream(format))
      } catch (_) {}
    }

    const text = await new Response(body).text()

    if (!text) {
      return new Response(JSON.stringify({ error: 'empty body from yad2', status: resp.status }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      })
    }

    let data
    try {
      data = JSON.parse(text)
    } catch (e) {
      return new Response(JSON.stringify({ error: 'invalid json', body: text.slice(0, 500) }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      })
    }

    // Normalise feed response → always {data: [...items]} so callers stay unchanged
    let normalized = data
    if (type === 'feed') {
      const items = (
        data?.data?.feed   ||   // most common feed structure
        data?.data?.items  ||
        data?.feed         ||
        (Array.isArray(data?.data) ? data.data : null) ||
        []
      )
      normalized = { data: items, total: data?.data?.totalItems ?? items.length }
    }

    return new Response(JSON.stringify(normalized), {
      status: resp.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    })
  }
}
