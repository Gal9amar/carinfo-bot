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
    const rows         = url.searchParams.get('rows') || '100'

    if (!manufacturer && !model) {
      return new Response(JSON.stringify({ error: 'missing manufacturer or model param' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      })
    }

    let yad2url = `https://gw.yad2.co.il/lookalike/vehicles/cars?rows=${rows}`
    if (manufacturer) yad2url += `&manufacturer=${manufacturer}`
    if (model)        yad2url += `&model=${model}`
    if (year)         yad2url += `&year=${year}`

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

    // Let Cloudflare's DecompressionStream handle gzip — pipe through it
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

    return new Response(JSON.stringify(data), {
      status: resp.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    })
  }
}
