#!/usr/bin/env python3
"""
Local Google Drive OAuth 2.0 Authorization Script (Sprint #36.15 / Etapa 5.5)

Executes locally on the owner's Mac to grant 1-time offline authorization for
Google Drive persistence using the minimal scope: 'https://www.googleapis.com/auth/drive.file'.

Security Controls & Invariants:
1. Reads GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET strictly from environment variables.
2. Uses local loopback server (http://localhost:8080/) for Desktop Application OAuth flow.
3. Enforces strictly minimal scope: 'https://www.googleapis.com/auth/drive.file' (NO access to full Drive).
4. Does NOT save refresh tokens, secrets, or credentials to disk, logs, git, or project files.
5. Displays a secure 1-time summary directing the user to copy the refresh token directly to Vercel.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enforced Minimal Scope
REQUIRED_SCOPE = "https://www.googleapis.com/auth/drive.file"


import subprocess

def _set_vercel_env(var_name: str, var_val: str):
    """Sets a Vercel Production environment variable safely without exposing value."""
    if not var_val:
        return
    try:
        res = subprocess.run(
            ["npx", "vercel", "env", "add", var_name, "production", "--force"],
            input=f"{var_val}\n",
            text=True,
            capture_output=True,
            cwd=str(PROJECT_ROOT)
        )
        if res.returncode == 0:
            print(f"[VERCEL CONFIG]: Variable {var_name} configurada con éxito en Vercel Production.")
        else:
            print(f"[VERCEL CONFIG WARNING]: No se pudo configurar {var_name}: {res.stderr}")
    except Exception as e:
        print(f"[VERCEL CONFIG ERROR]: {e}")


def authorize():
    """Runs local OAuth 2.0 InstalledAppFlow to obtain refresh token."""
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()

    if not client_id or client_id in {"REDACTED", "YOUR_CLIENT_ID", ""}:
        print("ERROR: GOOGLE_OAUTH_CLIENT_ID environment variable is missing or invalid.")
        print("Usage: GOOGLE_OAUTH_CLIENT_ID='...' GOOGLE_OAUTH_CLIENT_SECRET='...' python3 scripts/google_drive_oauth_authorize.py")
        sys.exit(1)

    if not client_secret or client_secret in {"REDACTED", "YOUR_CLIENT_SECRET", ""}:
        print("ERROR: GOOGLE_OAUTH_CLIENT_SECRET environment variable is missing or invalid.")
        print("Usage: GOOGLE_OAUTH_CLIENT_ID='...' GOOGLE_OAUTH_CLIENT_SECRET='...' python3 scripts/google_drive_oauth_authorize.py")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/", "http://127.0.0.1:8080/"]
        }
    }

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        print("\n=======================================================")
        print("   AUTOMATON STORAGE - GOOGLE DRIVE OAUTH AUTHORIZER   ")
        print("=======================================================\n")
        print("Iniciando flujo de autorización en el navegador...")
        print(f"Permiso solicitado: {REQUIRED_SCOPE} (Acceso limitado solo a archivos creados por la app)\n")

        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=[REQUIRED_SCOPE]
        )

        creds = flow.run_local_server(
            host="localhost",
            port=8080,
            authorization_prompt_message="Abre la siguiente URL en tu navegador si no se abre automáticamente:\n{url}\n",
            success_message="¡Autorización completada con éxito! Puedes cerrar esta pestaña y volver a la Terminal.",
            open_browser=True,
            access_type="offline",
            prompt="consent"
        )

        refresh_token = creds.refresh_token

        print("\n=======================================================")
        print("          ¡AUTORIZACIÓN COMPLETADA CON ÉXITO!          ")
        print("=======================================================")
        print("1. Autorización completada: SI")
        print("2. Permiso concedido: drive.file (Acceso restringido)")
        print("3. Refresh token obtenido: SI")
        print("-------------------------------------------------------")
        print("Configurando automáticamente Vercel Production...\n")

        _set_vercel_env("GOOGLE_OAUTH_CLIENT_ID", client_id)
        _set_vercel_env("GOOGLE_OAUTH_CLIENT_SECRET", client_secret)
        _set_vercel_env("GOOGLE_OAUTH_REFRESH_TOKEN", refresh_token)
        _set_vercel_env("DURABLE_STORAGE_PROVIDER", "GOOGLE_DRIVE_OAUTH")

        print("\n=======================================================\n")

    except ImportError:
        print("ERROR: La librería 'google-auth-oauthlib' no está instalada en tu entorno Python.")
        print("Ejecuta: pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)
    except Exception as err:
        print(f"ERROR DURANTE AUTORIZACIÓN: {err}")
        sys.exit(1)


if __name__ == "__main__":
    authorize()

