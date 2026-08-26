import os
import json
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
            event = json.loads(post_data.decode('utf-8'))
            event_type = event.get('event_type')
            resource = event.get('resource', {})
            
            # Log Webhook Event
            print(f"[PAYPAL WEBHOOK EVENT] Type: {event_type} | ID: {event.get('id')}")

            # Verify event types
            accepted_events = [
                'CHECKOUT.ORDER.APPROVED',
                'PAYMENT.CAPTURE.COMPLETED',
                'PAYMENT.CAPTURE.PENDING',
                'CHECKOUT.PAYMENT-APPROVAL.REVERSED'
            ]

            if event_type in accepted_events:
                # Save event to local audit log
                log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio')
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
                resource_id = resource.get('id') or event.get('id') or 'MOCK_WH_ID'

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
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_wh, f, indent=2)

                # If completed payment, log to payment log as well
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
                        with open(pmt_file, 'w', encoding='utf-8') as f:
                            json.dump(existing_pmt, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'received': True, 'event_type': event_type}).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
