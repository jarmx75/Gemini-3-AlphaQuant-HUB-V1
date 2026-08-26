import os
import json
import urllib.request
import base64
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        body = {}
        try:
            body = json.loads(post_data.decode('utf-8'))
        except Exception:
            body = {}
            
        txn_id = body.get('txn_id') or body.get('orderID') or body.get('payment_id')
        email = body.get('email')

        # Fail-closed check against local verified payment logs (from IPN or Webhooks)
        log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio', 'paypal_payment_log.json')
        verified_record = None

        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    payments = json.load(f)
                    for p in payments:
                        if isinstance(p, dict) and p.get('verified'):
                            if txn_id and p.get('txn_id') == txn_id:
                                verified_record = p
                                break
                            if email and p.get('payer_email') == email:
                                verified_record = p
                                break
            except Exception:
                pass

        if verified_record:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'verified': True,
                'status': 'COMPLETED',
                'payment_record': verified_record,
                'architecture': 'PAYPAL_HOSTED_LINKS_WEBHOOK_IPN'
            }).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'verified': False,
                'status': 'AWAITING_INDEPENDENT_PAYPAL_VERIFICATION',
                'message': 'Audit completion requires asynchronous PayPal Webhook/IPN verification for Hosted Payment Link transaction.'
            }).encode())
