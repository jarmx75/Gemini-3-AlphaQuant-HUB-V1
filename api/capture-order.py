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

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        body = json.loads(post_data.decode('utf-8'))
        order_id = body.get('orderID')

        if not order_id:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'orderID is required'}).encode())
            return

        try:
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

            capture_req = urllib.request.Request(
                f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )

            with urllib.request.urlopen(capture_req, timeout=10) as capture_resp:
                capture_data = json.loads(capture_resp.read().decode())
                status = capture_data.get('status')
                is_completed = (status == 'COMPLETED')

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'verified': is_completed,
                    'orderID': order_id,
                    'status': status,
                    'details': capture_data
                }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
