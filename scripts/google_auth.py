#!/usr/bin/env python3
"""Minimal Google OAuth helper — only requests drive + spreadsheets scopes."""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

REDIRECT_URI = "http://localhost:3000/oauth2callback"
auth_code = None
server_instance = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Success! Close this window.</h1>")
            threading.Thread(target=lambda: (time.sleep(0.5), server_instance.shutdown()), daemon=True).start()


def main():
    global server_instance
    keys_path = sys.argv[1] if len(sys.argv) > 1 else "configs/gcp-oauth.keys.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "configs/google_credentials.json"

    flow = Flow.from_client_secrets_file(keys_path, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

    print(f"\nOpen this URL in your browser:\n\n{auth_url}\n")

    server_instance = HTTPServer(("localhost", 3000), Handler)
    threading.Thread(target=server_instance.serve_forever, daemon=True).start()

    import webbrowser
    webbrowser.open(auth_url)

    print("Waiting for authorization...")
    while not auth_code:
        time.sleep(0.5)

    flow.fetch_token(code=auth_code)
    creds = flow.credentials

    creds_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(creds_data, f, indent=2)

    print(f"Credentials saved to {out_path}")


if __name__ == "__main__":
    main()
