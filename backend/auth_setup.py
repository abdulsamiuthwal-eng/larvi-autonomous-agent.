"""
Larvi — Quick Google Authentication Setup
Run this script directly to authenticate your Google Account in 5 seconds!
Works with env vars OR credentials.json (auto-detects).
"""
import sys
import json
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings, BASE_DIR
from google_auth_oauthlib.flow import InstalledAppFlow


def authenticate():
    print("\n" + "=" * 60)
    print("  LARVI GOOGLE OAUTH SETUP")
    print("  Opening browser for Google Authentication...")
    print("=" * 60 + "\n")

    credentials_path = BASE_DIR / settings.GOOGLE_CREDENTIALS_PATH
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET

    # Try credentials.json first (if it has real values)
    use_file = False
    if credentials_path.exists():
        try:
            data = json.loads(credentials_path.read_text())
            cred_data = data.get("installed") or data.get("web") or {}
            cid = cred_data.get("client_id", "")
            csec = cred_data.get("client_secret", "")
            if cid and "USE_VERCEL" not in cid and "@" not in cid:
                use_file = True
        except Exception:
            pass

    if use_file:
        # Use credentials.json (has real values)
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            scopes=settings.GOOGLE_SCOPES
        )
    elif client_id and client_secret and "USE_VERCEL" not in client_id:
        # Use environment variables
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
            }
        }
        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_SCOPES
        )
    else:
        print("[Error] No valid credentials found!")
        print("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env or environment.\n")
        return

    creds = flow.run_local_server(port=0, prompt="consent")

    token_path = BASE_DIR / settings.GOOGLE_TOKEN_PATH
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print("\n" + "=" * 60)
    print("  AUTHENTICATION SUCCESSFUL!")
    print(f"  Token saved to: {token_path}")
    print("  Gmail and Google Calendar are now connected to Larvi.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    authenticate()
