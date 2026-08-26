import os
import json
import urllib.request
import base64
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        # Hosted Payment Links Canonical Mapping (No Orders API credentials required)
        hosted_links = {
            'QUANT_AUDIT_49': os.environ.get('PAYPAL_LINK_49', 'https://www.paypal.com/ncp/payment/SH9CKB2WSX728'),
            'QUANT_EXECUTION_REALITY_AUDIT_79': os.environ.get('PAYPAL_LINK_79', 'https://www.paypal.com/ncp/payment/TMMGL3YRC8PFN'),
            'COMPLETE_QUANT_VALIDATION_BUNDLE_96': os.environ.get('PAYPAL_LINK_96', 'https://www.paypal.com/ncp/payment/2Y3RX97HNWXY6')
        }
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = {}
        if content_length > 0:
            try:
                body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            except Exception:
                body = {}

        product_id = body.get('product_id', 'QUANT_AUDIT_49')
        payment_link = hosted_links.get(product_id, hosted_links['QUANT_AUDIT_49'])

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'DEPRECATED_MIGRATED_TO_HOSTED_LINKS',
            'product_id': product_id,
            'approvalUrl': payment_link,
            'message': 'PayPal Orders API has been migrated to PayPal Hosted Payment Links. Use direct hosted link.'
        }).encode())
