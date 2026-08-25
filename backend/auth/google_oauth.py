"""
Larvi — Google OAuth 2.0 Manager (Multi-User & Session-Aware)
Handles authentication token creation, storage, and auto-refresh
for Gmail and Google Calendar APIs on a per-session and global basis.
"""
import os
import json
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build

from config import settings, BASE_DIR

# Tokens directory for per-session token storage
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    TOKENS_DIR = Path("/tmp/tokens")
else:
    TOKENS_DIR = BASE_DIR / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)

# In-memory credentials cache: session_id -> Credentials
_session_credentials: dict[str, Credentials] = {}
# In-memory user info cache: session_id -> dict(email, name, picture)
_session_userinfo: dict[str, dict] = {}


def _get_token_path(session_id: Optional[str] = None) -> Path:
    """Get the token file path for a session or global default."""
    if session_id:
        # Sanitize session_id for filesystem safety
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return TOKENS_DIR / f"{safe_id}.json"
    return BASE_DIR / settings.GOOGLE_TOKEN_PATH


def save_credentials(creds: Credentials, session_id: Optional[str] = None) -> None:
    """Persist credentials to token file and in-memory cache."""
    if session_id:
        _session_credentials[session_id] = creds

    token_path = _get_token_path(session_id)
    with open(token_path, "w") as f:
        f.write(creds.to_json())


def get_session_credentials(session_id: Optional[str] = None) -> Optional[Credentials]:
    """
    Retrieve valid Google OAuth credentials for a specific session.
    Falls back to global token.json if no session token exists.
    Auto-refreshes expired tokens.
    """
    creds = None

    # 1. Check in-memory cache
    if session_id and session_id in _session_credentials:
        creds = _session_credentials[session_id]

    # 2. Check session token file
    if creds is None and session_id:
        session_token_path = _get_token_path(session_id)
        if session_token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(session_token_path), settings.GOOGLE_SCOPES
                )
                _session_credentials[session_id] = creds
            except Exception as e:
                print(f"[Auth] Error reading session token {session_id}: {e}")

    # 3. Fallback to global token.json
    if creds is None:
        global_token_path = BASE_DIR / settings.GOOGLE_TOKEN_PATH
        if global_token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(global_token_path), settings.GOOGLE_SCOPES
                )
            except Exception as e:
                print(f"[Auth] Error reading global token: {e}")

    # 4. Auto-refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(creds, session_id)
            print(f"[Auth] Token refreshed successfully for session: {session_id or 'global'}")
        except Exception as e:
            print(f"[Auth] Token refresh failed: {e}. Re-authentication required.")
            creds = None

    return creds if (creds and creds.valid) else None


def get_credentials() -> Optional[Credentials]:
    """Compatibility helper: gets default / global credentials."""
    return get_session_credentials(None)


def get_or_create_credentials(session_id: Optional[str] = None) -> Optional[Credentials]:
    """Main entry point used by service wrappers."""
    return get_session_credentials(session_id)


def is_authenticated(session_id: Optional[str] = None) -> bool:
    """Check if the given session has valid Google credentials."""
    return get_session_credentials(session_id) is not None


# ── Web OAuth Flow (Multi-User) ───────────────────────────────────────────────

def create_web_flow(redirect_uri: str) -> Flow:
    """Create a Google OAuth Flow object configured with Web redirect URI."""
    credentials_path = BASE_DIR / settings.GOOGLE_CREDENTIALS_PATH
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {credentials_path}.\n"
            "Please download Desktop or Web credentials from Google Cloud Console."
        )

    return Flow.from_client_secrets_file(
        str(credentials_path),
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=redirect_uri,
    )


def get_authorization_url(session_id: str, redirect_uri: str) -> tuple[str, str]:
    """
    Generate the Google OAuth consent URL for a user session.
    Attaches the session_id as the OAuth state parameter.
    """
    flow = create_web_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=session_id,
    )
    return auth_url, state


def exchange_code_for_credentials(code: str, redirect_uri: str, session_id: str) -> Credentials:
    """
    Exchange the authorization code from Google OAuth callback for access/refresh tokens.
    Saves the credentials specifically for the given session_id.
    """
    flow = create_web_flow(redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_credentials(creds, session_id)

    # Fetch and cache user profile info
    fetch_user_profile(creds, session_id)
    return creds


def fetch_user_profile(creds: Credentials, session_id: Optional[str] = None) -> dict:
    """Fetch user's email and name from Google UserInfo API."""
    try:
        oauth2_client = build("oauth2", "v2", credentials=creds)
        userinfo = oauth2_client.userinfo().get().execute()
        info = {
            "email": userinfo.get("email", ""),
            "name": userinfo.get("name", ""),
            "picture": userinfo.get("picture", ""),
        }
        if session_id:
            _session_userinfo[session_id] = info
        return info
    except Exception as e:
        print(f"[Auth] Could not fetch userinfo: {e}")
        return {"email": "", "name": "", "picture": ""}


def get_auth_status(session_id: Optional[str] = None) -> dict:
    """Return a detailed auth status dict for a specific session."""
    creds = get_session_credentials(session_id)
    if creds is None:
        return {
            "authenticated": False,
            "gmail_connected": False,
            "calendar_connected": False,
            "session_id": session_id,
            "message": "Not authenticated. Click 'Connect Google Account' to link Gmail & Calendar.",
        }

    user_info = _session_userinfo.get(session_id or "", {})
    if not user_info.get("email"):
        user_info = fetch_user_profile(creds, session_id)

    return {
        "authenticated": True,
        "gmail_connected": True,
        "calendar_connected": True,
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "session_id": session_id,
        "token_valid": creds.valid,
        "message": f"Connected as {user_info.get('email', 'Google Account')}",
    }


# ── Desktop CLI OAuth Flow (For auth_setup.py) ─────────────────────────────────

def run_oauth_flow() -> Credentials:
    """Run the desktop local server OAuth flow."""
    credentials_path = BASE_DIR / settings.GOOGLE_CREDENTIALS_PATH
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {credentials_path}.\n"
            "Please download it from Google Cloud Console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path), settings.GOOGLE_SCOPES
    )

    try:
        creds = flow.run_local_server(port=8080, prompt="consent")
    except OSError:
        creds = flow.run_local_server(port=0, prompt="consent")

    save_credentials(creds, None)
    print("[Auth] OAuth flow completed. Global token saved.")
    return creds
