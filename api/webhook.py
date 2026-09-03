import os
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

def _get_log_dir():
    if os.environ.get('PAYPAL_LOG_DIR'):
        d = os.environ['PAYPAL_LOG_DIR']
        os.makedirs(d, exist_ok=True)
        return d
    if os.environ.get('VERCEL') or os.path.exists('/tmp'):
        d = '/tmp/logs/portfolio'
        os.makedirs(d, exist_ok=True)
        return d
    d = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio'))
    os.makedirs(d, exist_ok=True)
    return d

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, paypal-transmission-id, paypal-transmission-sig')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            timestamp_utc = datetime.now(timezone.utc).isoformat()
            payload = json.loads(post_data.decode('utf-8'))
            
            action = payload.get('action')
            event_type = payload.get('event_type')
            resource = payload.get('resource', {})

            log_dir = _get_log_dir()
            onboarding_file = os.path.join(log_dir, 'onboarding_records.json')
            pmt_file = os.path.join(log_dir, 'paypal_payment_log.json')
            log_file = os.path.join(log_dir, 'paypal_webhooks.json')

            # 1. HANDLE CUSTOMER ONBOARDING EMAIL REGISTRATION FROM FRONTEND
            if action == 'CUSTOMER_ONBOARDING':
                txn_id = str(payload.get('transaction_id') or payload.get('tx') or payload.get('txn_id') or 'ONBOARDING_UNKNOWN').strip()
                email = str(payload.get('customer_email') or payload.get('email') or 'unknown@customer.com').strip()
                amount = str(payload.get('amount') or payload.get('amt') or '49.00').strip()
                currency = str(payload.get('currency') or payload.get('cc') or 'USD').strip()

                # Check if verified payment already exists in payment ledger (reconciliation check)
                existing_pmts = []
                if os.path.exists(pmt_file):
                    try:
                        with open(pmt_file, 'r', encoding='utf-8') as f:
                            loaded = json.load(f)
                            existing_pmts = loaded if isinstance(loaded, list) else loaded.get('payments', [])
                    except Exception:
                        existing_pmts = []

                is_verified_payment = any(
                    isinstance(p, dict) and p.get('verified') is True and str(p.get('txn_id', '')).strip() == txn_id
                    for p in existing_pmts
                )

                # Strictly enforce fail-closed invariant: PAYMENT_RETURN != PAYMENT_COMPLETED
                status_entregado = 'VERIFIED_MATCHED_FULFILLMENT_AUTHORIZED' if is_verified_payment else 'PENDING_VERIFICATION'

                print(f"[ONBOARDING REGISTERED]: Transaction_ID={txn_id} | Email={email} | Verified_Payment={is_verified_payment} | Status_Entregado={status_entregado}")

                record = {
                    'transaction_id': txn_id,
                    'customer_email': email,
                    'amount': amount,
                    'currency': currency,
                    'status_entregado': status_entregado,
                    'is_verified_payment': is_verified_payment,
                    'registered_at_utc': timestamp_utc
                }

                existing_onboarding = []
                if os.path.exists(onboarding_file):
                    try:
                        with open(onboarding_file, 'r', encoding='utf-8') as f:
                            existing_onboarding = json.load(f)
                    except Exception:
                        existing_onboarding = []

                existing_onboarding.append(record)
                try:
                    with open(onboarding_file, 'w', encoding='utf-8') as f:
                        json.dump(existing_onboarding, f, indent=2)
                except Exception:
                    pass

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Onboarding registered cleanly in PENDING_VERIFICATION state',
                    'transaction_id': txn_id,
                    'customer_email': email,
                    'status_entregado': status_entregado,
                    'reconciled': is_verified_payment,
                    'timestamp_utc': timestamp_utc
                }).encode())
                return

            # 2. HANDLE PAYPAL ASYNCHRONOUS WEBHOOK EVENTS
            print(f"[PAYPAL WEBHOOK EVENT] Type: {event_type} | ID: {payload.get('id')}")

            accepted_events = [
                'CHECKOUT.ORDER.APPROVED',
                'PAYMENT.CAPTURE.COMPLETED',
                'PAYMENT.CAPTURE.PENDING',
                'CHECKOUT.PAYMENT-APPROVAL.REVERSED'
            ]

            if event_type in accepted_events:
                amount_val = resource.get('amount', {}).get('value') or '0.00'
                product_id = 'QUANT_AUDIT_49'
                if str(amount_val).strip() in ['79.00', '79']:
                    product_id = 'QUANT_EXECUTION_REALITY_AUDIT_79'
                elif str(amount_val).strip() in ['96.00', '96']:
                    product_id = 'COMPLETE_QUANT_VALIDATION_BUNDLE_96'

                payer_email = resource.get('payer', {}).get('email_address') or resource.get('payer_email') or 'unknown@customer.com'
                resource_id = str(resource.get('id') or payload.get('id') or 'MOCK_WH_ID').strip()

                existing_wh = []
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            existing_wh = json.load(f)
                    except Exception:
                        existing_wh = []
                        
                existing_wh.append({
                    'event_type': event_type,
                    'resource_id': resource_id,
                    'status': resource.get('status'),
                    'amount': amount_val,
                    'currency': resource.get('amount', {}).get('currency_code', 'USD'),
                    'product_id': product_id,
                    'payer_email': payer_email
                })
                
                try:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        json.dump(existing_wh, f, indent=2)
                except Exception:
                    pass

                if event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.APPROVED']:
                    existing_pmt = []
                    if os.path.exists(pmt_file):
                        try:
                            with open(pmt_file, 'r', encoding='utf-8') as f:
                                existing_pmt = json.load(f)
                        except Exception:
                            existing_pmt = []
                    
                    if not any(x.get('txn_id') == resource_id for x in existing_pmt if isinstance(x, dict)):
                        existing_pmt.append({
                            'source': 'PAYPAL_WEBHOOK',
                            'verified': True,
                            'txn_id': resource_id,
                            'payment_status': resource.get('status', 'COMPLETED'),
                            'amount': amount_val,
                            'currency': resource.get('amount', {}).get('currency_code', 'USD'),
                            'payer_email': payer_email,
                            'product_id': product_id,
                            'timestamp_utc': timestamp_utc
                        })
                        try:
                            with open(pmt_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_pmt, f, indent=2)
                        except Exception:
                            pass

                    # RECONCILIATION: Check if an onboarding record was waiting for this txn_id
                    if os.path.exists(onboarding_file):
                        try:
                            with open(onboarding_file, 'r', encoding='utf-8') as f:
                                onboarding_list = json.load(f)
                            updated = False
                            for rec in onboarding_list:
                                if isinstance(rec, dict) and rec.get('transaction_id') == resource_id:
                                    rec['status_entregado'] = 'VERIFIED_MATCHED_FULFILLMENT_AUTHORIZED'
                                    rec['is_verified_payment'] = True
                                    rec['reconciled_at_utc'] = timestamp_utc
                                    updated = True
                            if updated:
                                with open(onboarding_file, 'w', encoding='utf-8') as f:
                                    json.dump(onboarding_list, f, indent=2)
                                print(f"[RECONCILIATION SUCCESS]: Transaction_ID={resource_id} matched with pending onboarding lead! Fulfillment Authorized.")
                        except Exception as rec_err:
                            print(f"[RECONCILIATION ERROR]: {rec_err}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'received': True, 'event_type': event_type}).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
