import os
import json
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler

LOGS_PORTFOLIO_DIR = Path('/tmp/portfolio_logs')
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
LEADS_FILE = LOGS_PORTFOLIO_DIR / 'quiz_leads.json'

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
            quiz_data = json.loads(post_data.decode('utf-8'))
            name = quiz_data.get('name', 'Anonymous')
            email = quiz_data.get('email', '')
            strategy_type = quiz_data.get('strategy_type', 'Quant StatArb')
            trade_count = quiz_data.get('trade_count', '100-500')
            max_drawdown = quiz_data.get('max_drawdown', '10-25%')

            lead_id = f"lead_{uuid.uuid4().hex[:8]}"

            # Score Lead
            score = 50
            if '500+' in trade_count or '100-500' in trade_count:
                score += 25
            if 'Quant' in strategy_type or 'Trend' in strategy_type:
                score += 15
            if '@' in email:
                score += 10

            classification = 'HOT' if score >= 80 else ('WARM' if score >= 60 else 'NURTURE')

            record = {
                'lead_id': lead_id,
                'name': name,
                'email': email,
                'strategy_type': strategy_type,
                'trade_count': trade_count,
                'max_drawdown': max_drawdown,
                'score': score,
                'classification': classification,
                'timestamp': '2026-08-24T02:21:45Z'
            }

            existing = []
            if LEADS_FILE.exists():
                try:
                    with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception:
                    existing = []

            existing.append(record)
            with open(LEADS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'lead_id': lead_id,
                'score': score,
                'classification': classification,
                'message': 'Strategy diagnostic quiz submitted successfully!'
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
