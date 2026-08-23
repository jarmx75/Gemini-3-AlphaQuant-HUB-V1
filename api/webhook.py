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
                # Save event to local audit log if applicable
                log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'portfolio')
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, 'paypal_webhooks.json')
                
                existing = []
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            existing = json.load(f)
                    except Exception:
                        existing = []
                        
                existing.append({
                    'event_type': event_type,
                    'resource_id': resource.get('id'),
                    'status': resource.get('status'),
                    'amount': resource.get('amount', {}).get('value'),
                    'currency': resource.get('amount', {}).get('currency_code')
                })
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'received': True, 'event_type': event_type}).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
