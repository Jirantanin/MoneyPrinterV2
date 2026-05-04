"""
Run this script ONCE to authenticate with YouTube Data API.
It will open a browser for you to login, then save token.json.
After that, MoneyPrinterV2 will use token.json automatically.

Usage:
    python src/youtube_auth.py
"""

import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRETS = os.path.join(ROOT_DIR, "client_secrets.json")
TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")


def authenticate():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS):
                print(f"[ERROR] client_secrets.json not found at: {CLIENT_SECRETS}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    print(f"[OK] Authentication successful. token.json saved to: {TOKEN_PATH}")
    return creds


if __name__ == "__main__":
    authenticate()
