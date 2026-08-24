import os
import json
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler

LOGS_PORTFOLIO_DIR = Path('/tmp/portfolio_logs')
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
ANALYTICS_FILE = LOGS_PORTFOLIO_DIR / 'landing_analytics.json'

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'

        try:
            event_data = json.loads(post_data.decode('utf-8'))
            event_type = event_data.get('event_type', 'page_visit')
            page_url = event_data.get('page_url', 'https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/')
            referrer = event_data.get('referrer', '')
            user_agent = self.headers.get('User-Agent', '')

            event_id = f"evt_{uuid.uuid4().hex[:8]}"

            record = {
                'event_id': event_id,
                'event_type': event_type,
                'page_url': page_url,
                'referrer': referrer,
                'timestamp': '2026-08-24T02:37:50Z'
            }

            existing = []
            if ANALYTICS_FILE.exists():
                try:
                    with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception:
                    existing = []

            existing.append(record)
            with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'event_id': event_id,
                'event_type': event_type,
                'total_events': len(existing)
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
