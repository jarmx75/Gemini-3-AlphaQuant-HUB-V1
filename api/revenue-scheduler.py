"""
Production Revenue Scheduler Endpoint (Vercel / Production Cron API)

Path: /api/revenue-scheduler
"""

import json, os, sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# Add root path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.economics.autonomous_revenue_orchestrator import AutonomousRevenueOrchestrator


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.handle_schedule()

    def do_POST(self):
        self.handle_schedule()

    def handle_schedule(self):
        try:
            orchestrator = AutonomousRevenueOrchestrator()
            res = orchestrator.run_scheduled_cycle()

            body = json.dumps({
                "status": "OK",
                "scheduler_execution": res,
                "environment": "PRODUCTION_CRON"
            }).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err_body = json.dumps({"status": "ERROR", "message": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
