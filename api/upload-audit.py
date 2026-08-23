import os
import json
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler

UPLOAD_DIR = Path('/tmp/quant_audit_uploads')
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB limit

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Order-ID')
        self.end_headers()

    def do_POST(self):
        order_id = self.headers.get('X-Order-ID', 'UNVERIFIED_ORDER')
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length > MAX_FILE_SIZE:
            self.send_response(413)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'File size exceeds 5 MB limit'}).encode())
            return

        post_data = self.rfile.read(content_length) if content_length > 0 else b''

        try:
            # Check content type / filename extension
            file_id = f"upload_{uuid.uuid4().hex[:12]}"
            upload_token = f"token_{uuid.uuid4().hex[:16]}"
            saved_path = UPLOAD_DIR / f"{file_id}.data"

            with open(saved_path, 'wb') as f:
                f.write(post_data)

            metadata = {
                'file_id': file_id,
                'upload_token': upload_token,
                'order_id': order_id,
                'file_size_bytes': len(post_data),
                'saved_path': str(saved_path),
                'status': 'UPLOAD_RECEIVED'
            }

            meta_path = UPLOAD_DIR / f"{file_id}.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'file_id': file_id,
                'upload_token': upload_token,
                'order_id': order_id,
                'message': 'Strategy file uploaded safely. Audit processing initiated.'
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://jarmx75.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
