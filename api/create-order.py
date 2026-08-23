import os
import json
import urllib.request
import base64
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        client_id = os.environ.get('PAYPAL_CLIENT_ID')
        client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')

        if not client_id or not client_secret:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Server PayPal credentials missing'}).encode())
            return

        try:
            # 1. Get OAuth Token from PayPal LIVE
            auth_str = f"{client_id}:{client_secret}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()

            token_req = urllib.request.Request(
                'https://api-m.paypal.com/v1/oauth2/token',
                data=b'grant_type=client_credentials',
                headers={
                    'Authorization': f'Basic {b64_auth}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                method='POST'
            )

            with urllib.request.urlopen(token_req, timeout=10) as resp:
                token_data = json.loads(resp.read().decode())
                access_token = token_data['access_token']

            # 2. Create PayPal LIVE Order ($49.00 USD)
            order_payload = json.dumps({
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {
                        'currency_code': 'USD',
                        'value': '49.00'
                    },
                    'description': 'Automaton Quant Audit Verification ($49 USD)'
                }],
                'application_context': {
                    'brand_name': 'Automaton Quant Audit',
                    'landing_page': 'NO_PREFERENCE',
                    'user_action': 'PAY_NOW',
                    'return_url': 'https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/sample.html?status=success',
                    'cancel_url': 'https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/?status=cancelled'
                }
            }).encode()

            order_req = urllib.request.Request(
                'https://api-m.paypal.com/v2/checkout/orders',
                data=order_payload,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )

            with urllib.request.urlopen(order_req, timeout=10) as order_resp:
                order_data = json.loads(order_resp.read().decode())
                order_id = order_data['id']
                links = order_data.get('links', [])
                approve_url = next((l['href'] for l in links if l['rel'] in ['approve', 'payer-action']), f"https://www.paypal.com/checkoutnow?token={order_id}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'orderID': order_id,
                    'approvalUrl': approve_url,
                    'status': order_data.get('status')
                }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
