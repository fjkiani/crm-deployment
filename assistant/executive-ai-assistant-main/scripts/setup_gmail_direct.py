#!/usr/bin/env python3
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


def main():
    base = Path(__file__).resolve().parents[1] / "eaia" / ".secrets"
    base.mkdir(parents=True, exist_ok=True)
    secrets = base / "secrets.json"
    token = base / "token.json"
    if not secrets.exists():
        raise SystemExit(f"Missing client secrets at {secrets}")

    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
            token.write_text(creds.to_json())
            print("Refreshed existing token.")
            return

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(port=0)
    token.write_text(creds.to_json())
    print(f"Saved token at {token}")


if __name__ == "__main__":
    main()

