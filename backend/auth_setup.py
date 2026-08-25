"""
Larvi — Quick Google Authentication Setup
Run this script directly to authenticate your Google Account in 5 seconds!
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings, BASE_DIR
from google_auth_oauthlib.flow import InstalledAppFlow


def authenticate():
    credentials_path = BASE_DIR / settings.GOOGLE_CREDENTIALS_PATH

    if not credentials_path.exists():
        print(f"\n[Error] {credentials_path} not found.")
        print("Please ensure credentials.json is placed in the backend folder.\n")
        return

    print("\n" + "=" * 60)
    print("  LARVI GOOGLE OAUTH SETUP")
    print("  Opening browser for Google Authentication...")
    print("=" * 60 + "\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path),
        scopes=settings.GOOGLE_SCOPES
    )

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
