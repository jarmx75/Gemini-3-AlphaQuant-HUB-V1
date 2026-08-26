import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler

PAYPAL_LIVE_IPN_URL = "https://ipnpb.paypal.com/cgi-bin/webscr"
PAYPAL_LIVE_IPN_FALLBACK_URL = "https://www.paypal.com/cgi-bin/webscr"
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
            timestamp_utc = datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()
            
            # Parse form-encoded IPN payload
            parsed_params = urllib.parse.parse_qs(post_body.decode('utf-8', errors='ignore'))
            ipn_dict = {k: v[0] if len(v) == 1 else v for k, v in parsed_params.items()}

            # Extract fields
            txn_id = ipn_dict.get('txn_id') or ipn_dict.get('ipn_track_id')
            payment_status = ipn_dict.get('payment_status') or ipn_dict.get('status') or 'UNKNOWN'
            mc_gross = ipn_dict.get('mc_gross') or ipn_dict.get('payment_gross') or '0.00'
            mc_currency = ipn_dict.get('mc_currency', 'USD')
            payer_email = ipn_dict.get('payer_email', 'unknown@customer.com')

            # Determine product matching based on exact amount
            amount_str = str(mc_gross).strip()
            product_id = 'QUANT_AUDIT_49'
            if amount_str in ['79.00', '79']:
                product_id = 'QUANT_EXECUTION_REALITY_AUDIT_79'
            elif amount_str in ['96.00', '96']:
                product_id = 'COMPLETE_QUANT_VALIDATION_BUNDLE_96'

            # Prepare validation request back to PayPal
            validate_body = b'cmd=_notify-validate&' + post_body
            mode = os.environ.get('PAYPAL_MODE', 'LIVE')
            verify_url = PAYPAL_SANDBOX_IPN_URL if mode == 'SANDBOX' else PAYPAL_LIVE_IPN_URL

            is_verified = False
            if post_body:
                req = urllib.request.Request(
                    verify_url,
                    data=validate_body,
                    headers={'User-Agent': 'Automaton-Quant-Audit-IPN-Verifier'},
                    method='POST'
                )

                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res_text = resp.read().decode('utf-8').strip()
                        if res_text == 'VERIFIED':
                            is_verified = True
                except Exception:
                    # Fallback to secondary production endpoint if live
                    if mode != 'SANDBOX':
                        try:
                            req_fallback = urllib.request.Request(
                                PAYPAL_LIVE_IPN_FALLBACK_URL,
                                data=validate_body,
                                headers={'User-Agent': 'Automaton-Quant-Audit-IPN-Verifier'},
                                method='POST'
                            )
                            with urllib.request.urlopen(req_fallback, timeout=10) as resp_fb:
                                if resp_fb.read().decode('utf-8').strip() == 'VERIFIED':
                                    is_verified = True
                        except Exception as net_err:
                            print(f"[IPN WARNING] Handshake error: {net_err}")

            # Directories & files for logging
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio')
            os.makedirs(log_dir, exist_ok=True)
            events_log_file = os.path.join(log_dir, 'paypal_ipn_events.jsonl')
            verified_pmt_file = os.path.join(log_dir, 'paypal_payment_log.json')

            # Check existing payments for primary txn_id idempotency
            existing_pmts = []
            if os.path.exists(verified_pmt_file):
                try:
                    with open(verified_pmt_file, 'r', encoding='utf-8') as f:
                        existing_pmts = json.load(f)
                except Exception:
                    existing_pmts = []

            is_duplicate = False
            if txn_id and any(isinstance(x, dict) and x.get('txn_id') == txn_id for x in existing_pmts):
                is_duplicate = True

            idempotency_status = 'REJECTED'
            if is_verified and payment_status.upper() == 'COMPLETED':
                if is_duplicate:
                    idempotency_status = 'DUPLICATE_IGNORED'
                else:
                    idempotency_status = 'NEW_VERIFIED'
                    existing_pmts.append({
                        'source': 'PAYPAL_IPN',
                        'verified': True,
                        'txn_id': txn_id,
                        'payment_status': payment_status,
                        'amount': mc_gross,
                        'currency': mc_currency,
                        'payer_email': payer_email,
                        'product_id': product_id,
                        'timestamp_utc': timestamp_utc
                    })
                    with open(verified_pmt_file, 'w', encoding='utf-8') as f:
                        json.dump(existing_pmts, f, indent=2)

            # Log to append-only jsonl stream
            raw_event_record = {
                'timestamp_utc': timestamp_utc,
                'txn_id': txn_id or 'UNKNOWN_TXN',
                'verified': is_verified,
                'payment_status': payment_status,
                'amount': mc_gross,
                'currency': mc_currency,
                'payer_email': payer_email,
                'product_id': product_id,
                'idempotency_status': idempotency_status,
                'mode': mode
            }

            with open(events_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(raw_event_record) + '\n')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'received': True,
                'verified': is_verified,
                'txn_id': txn_id,
                'idempotency_status': idempotency_status
            }).encode())

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
