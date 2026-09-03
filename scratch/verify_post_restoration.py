import os
import sys
import hashlib
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

verify_file = ".env.verify.tmp"

SENSITIVE_HASH = "3930fb7a9a99"

try:
    subprocess.run(["npx", "vercel", "env", "pull", verify_file, "--environment", "production", "--yes"], capture_output=True, check=True)
    
    env_vars = {}
    with open(verify_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.rstrip("\r\n")
            if "=" in line_str and not line_str.startswith("#"):
                key, val = line_str.split("=", 1)
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                env_vars[key] = val

    cid = env_vars.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    csec = env_vars.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    refr = env_vars.get("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip()

    cid_len, cid_hash = len(cid), hashlib.sha256(cid.encode("utf-8")).hexdigest()[:12]
    csec_len, csec_hash = len(csec), hashlib.sha256(csec.encode("utf-8")).hexdigest()[:12]
    refr_len, refr_hash = len(refr), hashlib.sha256(refr.encode("utf-8")).hexdigest()[:12]

    print("=== POST-RESTORATION VERCEL ENV INTEGRITY AUDIT ===")
    print(f"GOOGLE_OAUTH_CLIENT_ID: len={cid_len}, hash12={cid_hash} (Sensitive: {'SI' if cid_hash == SENSITIVE_HASH else 'NO'})")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET: len={csec_len}, hash12={csec_hash} (Sensitive: {'SI' if csec_hash == SENSITIVE_HASH else 'NO'})")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN: len={refr_len}, hash12={refr_hash} (Sensitive: {'SI' if refr_hash == SENSITIVE_HASH else 'NO'})")

    if cid_hash != SENSITIVE_HASH and csec_hash != SENSITIVE_HASH and refr_hash != SENSITIVE_HASH and cid_len > 20 and refr_len > 20:
        print("RESULT: RESTORATION_VERIFIED_CLEAN")
    else:
        print("RESULT: CORRUPTION_DETECTED")

finally:
    if os.path.exists(verify_file):
        os.remove(verify_file)
        print(".env.verify.tmp deleted cleanly.")
