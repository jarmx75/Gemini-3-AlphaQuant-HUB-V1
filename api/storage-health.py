"""
Serverless Endpoint: Storage Health Check (Sprint #36.11 / Etapa 4.3)

Provides a lightweight, read-only status endpoint (/api/storage-health) to verify:
- Durable storage configuration (S3 / Google Drive)
- Service account connectivity and folder metadata access
- Fail-closed security status

Security & Invariants:
1. Accepts ONLY GET requests (405 Method Not Allowed for POST/PUT/DELETE).
2. Performs ONLY folder metadata read (health_check).
3. NEVER lists files, NEVER uploads/edits/deletes files.
4. NEVER exposes secrets, folder IDs, emails, endpoints, or stack traces.
5. Even when health == 'HEALTHY', returns commercial_fulfillment_readiness = 'PARTIAL' (NEVER 'READY').
"""

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()

    def do_POST(self):
        self.send_response(405)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'error': 'METHOD_NOT_ALLOWED',
            'message': 'Only GET requests are accepted by /api/storage-health'
        }).encode('utf-8'))

    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        self.do_POST()

    def do_GET(self):
        try:
            from src.economics.durable_storage import get_durable_storage_engine
            engine = get_durable_storage_engine()
            status = engine.get_storage_status()

            configured = status.get('durable_storage_configured', False)
            health = status.get('durable_storage_health', 'NOT_CONFIGURED')
            provider = status.get('durable_storage_provider', 'NOT_CONFIGURED')

            if health in {'HEALTHY', 'CONFIGURED_LITE'}:
                commercial_readiness = 'PARTIAL'
                http_code = 200
            else:
                commercial_readiness = 'NOT_READY'
                http_code = 503

            response_body = {
                'service': 'durable_storage',
                'provider': provider,
                'configured': configured,
                'health': health,
                'commercial_fulfillment_readiness': commercial_readiness
            }
        except Exception:
            http_code = 503
            response_body = {
                'service': 'durable_storage',
                'provider': 'UNKNOWN',
                'configured': False,
                'health': 'STORAGE_ERROR',
                'commercial_fulfillment_readiness': 'NOT_READY'
            }

        self.send_response(http_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.end_headers()
        self.wfile.write(json.dumps(response_body, indent=2).encode('utf-8'))
