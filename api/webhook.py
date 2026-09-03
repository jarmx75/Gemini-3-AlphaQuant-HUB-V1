import os
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

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

            # Log Webhook / Onboarding Event
            if action == 'CUSTOMER_ONBOARDING':
                txn_id = payload.get('transaction_id') or payload.get('tx') or payload.get('txn_id') or 'ONBOARDING_UNKNOWN'
                email = payload.get('customer_email') or payload.get('email') or 'unknown@customer.com'
                amount = payload.get('amount') or payload.get('amt') or '49.00'
                currency = payload.get('currency') or payload.get('cc') or 'USD'
                status_entregado = payload.get('status_entregado', 'QUEUED_FOR_DELIVERY')

                print(f"[CUSTOMER ONBOARDING REGISTERED] Transaction_ID: {txn_id} | Email: {email} | Amount: ${amount} {currency} | Status_Entregado: {status_entregado}")

                log_dir = '/tmp/logs/portfolio' if os.environ.get('VERCEL') or os.path.exists('/tmp') else os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio')
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except OSError:
                    log_dir = '/tmp/logs/portfolio'
                    os.makedirs(log_dir, exist_ok=True)

                record = {
                    'transaction_id': txn_id,
                    'customer_email': email,
                    'amount': amount,
                    'currency': currency,
                    'status_entregado': status_entregado,
                    'registered_at_utc': timestamp_utc
                }

                log_file = os.path.join(log_dir, 'onboarding_records.json')
                existing = []
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            existing = json.load(f)
                    except Exception:
                        existing = []
                existing.append(record)
                try:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        json.dump(existing, f, indent=2)
                except Exception:
                    pass

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Onboarding registered successfully',
                    'transaction_id': txn_id,
                    'customer_email': email,
                    'status_entregado': status_entregado,
                    'timestamp_utc': timestamp_utc
                }).encode())
                return

            print(f"[PAYPAL WEBHOOK EVENT] Type: {event_type} | ID: {payload.get('id')}")

            accepted_events = [
                'CHECKOUT.ORDER.APPROVED',
                'PAYMENT.CAPTURE.COMPLETED',
                'PAYMENT.CAPTURE.PENDING',
                'CHECKOUT.PAYMENT-APPROVAL.REVERSED'
            ]

            if event_type in accepted_events:
                if os.environ.get('PAYPAL_LOG_DIR'):
                    log_dir = os.environ['PAYPAL_LOG_DIR']
                elif os.environ.get('VERCEL') or os.path.exists('/tmp'):
                    log_dir = '/tmp/logs/portfolio'
                else:
                    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio')
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except OSError:
                    log_dir = '/tmp/logs/portfolio'
                    os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, 'paypal_webhooks.json')
                pmt_file = os.path.join(log_dir, 'paypal_payment_log.json')
                
                amount_val = resource.get('amount', {}).get('value') or '0.00'
                product_id = 'QUANT_AUDIT_49'
                if str(amount_val).strip() in ['79.00', '79']:
                    product_id = 'QUANT_EXECUTION_REALITY_AUDIT_79'
                elif str(amount_val).strip() in ['96.00', '96']:
                    product_id = 'COMPLETE_QUANT_VALIDATION_BUNDLE_96'

                payer_email = resource.get('payer', {}).get('email_address') or resource.get('payer_email') or 'unknown@customer.com'
                resource_id = resource.get('id') or payload.get('id') or 'MOCK_WH_ID'

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
                            'product_id': product_id
                        })
                        try:
                            with open(pmt_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_pmt, f, indent=2)
                        except Exception:
                            pass

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
