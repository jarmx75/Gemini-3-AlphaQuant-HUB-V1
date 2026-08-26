import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

PAYPAL_LIVE_IPN_URL = "https://ipnpb.paypal.com/cgi-bin/webscr"
PAYPAL_SANDBOX_IPN_URL = "https://ipnpb.sandbox.paypal.com/cgi-bin/webscr"


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_length) if content_length > 0 else b''

        try:
            # Parse form-encoded IPN payload
            parsed_params = urllib.parse.parse_qs(post_body.decode('utf-8', errors='ignore'))
            ipn_dict = {k: v[0] if len(v) == 1 else v for k, v in parsed_params.items()}

            # Prepare validation request back to PayPal
            validate_body = b'cmd=_notify-validate&' + post_body
            mode = os.environ.get('PAYPAL_MODE', 'LIVE')
            verify_url = PAYPAL_SANDBOX_IPN_URL if mode == 'SANDBOX' else PAYPAL_LIVE_IPN_URL

            req = urllib.request.Request(
                verify_url,
                data=validate_body,
                headers={'User-Agent': 'Automaton-Quant-Audit-IPN-Verifier'},
                method='POST'
            )

            is_verified = False
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    res_text = resp.read().decode('utf-8').strip()
                    if res_text == 'VERIFIED':
                        is_verified = True
            except Exception as net_err:
                print(f"[IPN WARNING] Handshake error: {net_err}")

            txn_id = ipn_dict.get('txn_id') or ipn_dict.get('ipn_track_id') or 'MOCK_TXN'
            payment_status = ipn_dict.get('payment_status') or ipn_dict.get('status') or 'UNKNOWN'
            mc_gross = ipn_dict.get('mc_gross') or ipn_dict.get('payment_gross') or '0.00'
            mc_currency = ipn_dict.get('mc_currency', 'USD')
            payer_email = ipn_dict.get('payer_email', 'unknown@customer.com')

            # Determine product matching
            product_id = 'QUANT_AUDIT_49'
            if str(mc_gross).strip() in ['79.00', '79']:
                product_id = 'QUANT_EXECUTION_REALITY_AUDIT_79'
            elif str(mc_gross).strip() in ['96.00', '96']:
                product_id = 'COMPLETE_QUANT_VALIDATION_BUNDLE_96'

            log_entry = {
                'source': 'PAYPAL_IPN',
                'verified': is_verified,
                'txn_id': txn_id,
                'payment_status': payment_status,
                'amount': mc_gross,
                'currency': mc_currency,
                'payer_email': payer_email,
                'product_id': product_id,
                'raw': ipn_dict
            }

            # Append to log
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'paypal_payment_log.json')

            existing = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception:
                    existing = []

            # Avoid duplicates
            if not any(x.get('txn_id') == txn_id for x in existing if isinstance(x, dict)):
                existing.append(log_entry)
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'received': True, 'verified': is_verified, 'txn_id': txn_id}).encode())

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
