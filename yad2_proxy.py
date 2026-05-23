"""
Yad2 proxy server — runs on Oracle Cloud IL (Israeli IP) to bypass Yad2 geo-block.
Usage: python yad2_proxy.py
Listens on 0.0.0.0:8080, forwards /yad2 requests to gw.yad2.co.il
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import urllib.request
import urllib.error
import json
import os
import gzip
import zlib

SECRET = os.environ.get("YAD2_PROXY_SECRET", "carinfo2026")
YAD2_BASE = "https://gw.yad2.co.il/lookalike/vehicles/cars"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.yad2.co.il/vehicles/cars",
    "Origin": "https://www.yad2.co.il",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[proxy] {self.address_string()} {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/yad2":
            self._respond(404, {"error": "not found"})
            return

        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # Auth check
        if params.get("secret") != SECRET:
            self._respond(403, {"error": "forbidden"})
            return

        # Build Yad2 URL — forward only relevant params
        yad2_params = {}
        if params.get("manufacturer"):
            yad2_params["manufacturer"] = params["manufacturer"]
        if params.get("model"):
            yad2_params["model"] = params["model"]
        if params.get("year"):
            yad2_params["year"] = params["year"]
        yad2_params["rows"] = params.get("rows", "100")

        yad2_url = f"{YAD2_BASE}?{urlencode(yad2_params)}"
        print(f"[proxy] → {yad2_url}")

        try:
            req = urllib.request.Request(yad2_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                encoding = resp.headers.get("Content-Encoding", "")

            # Decompress if needed
            if "gzip" in encoding:
                raw = gzip.decompress(raw)
            elif "deflate" in encoding:
                raw = zlib.decompress(raw)
            elif "br" in encoding:
                try:
                    import brotli
                    raw = brotli.decompress(raw)
                except ImportError:
                    pass

            # Validate JSON
            data = json.loads(raw.decode("utf-8"))
            self._respond(200, data)

        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            print(f"[proxy] Yad2 HTTP {e.code}: {body}")
            self._respond(502, {"error": f"yad2 http {e.code}", "detail": body})
        except Exception as e:
            print(f"[proxy] error: {e}")
            self._respond(502, {"error": str(e)})

    def _respond(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    host, port = "0.0.0.0", 8080
    print(f"[proxy] listening on {host}:{port}")
    HTTPServer((host, port), ProxyHandler).serve_forever()
