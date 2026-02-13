"""
Google Drive integration — OAuth2 (credentials.json).

Auth flow:
  - First run: opens browser for consent → saves token.json
  - Subsequent runs: loads token.json, refreshes if expired
  - token.json path: configurable via GOOGLE_TOKEN_JSON env var

Config (env vars):
  GOOGLE_CREDENTIALS_JSON  — path to credentials.json (required)
  GOOGLE_TOKEN_JSON        — path to token.json (default: same dir as credentials)
"""
import io
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config import GOOGLE_DRIVE_SCOPES

_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
_TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_JSON",
    str(Path(_CREDENTIALS_PATH).parent / "token.json"),
)


def _get_credentials() -> Credentials:
    """
    Load or refresh OAuth2 credentials.
    First run opens browser; token is cached for future runs.
    """
    creds = None

    if Path(_TOKEN_PATH).exists():
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, GOOGLE_DRIVE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(_CREDENTIALS_PATH).exists():
                raise FileNotFoundError(
                    f"credentials.json not found at: {_CREDENTIALS_PATH}\n"
                    "Set GOOGLE_CREDENTIALS_JSON env var to the correct path."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                _CREDENTIALS_PATH, GOOGLE_DRIVE_SCOPES
            )
            # Headless auth: print URL → user opens in browser → pastes code back
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(prompt="consent")
            print("\n" + "="*60)
            print("Google Drive Authentication Required")
            print("="*60)
            print(f"\n1. Open this URL in your browser:\n\n   {auth_url}\n")
            print("2. Sign in and grant access")
            print("3. Copy the authorization code and paste below\n")
            code = input("Authorization code: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials

        Path(_TOKEN_PATH).write_text(creds.to_json())

    return creds


def _build_service():
    return build("drive", "v3", credentials=_get_credentials(), cache_discovery=False)


def list_files(folder_id: str, page_size: int = 200) -> list[dict]:
    """
    List all files in a Drive folder (non-recursive).
    Returns list of {"id", "name", "mimeType"}.
    """
    service = _build_service()
    results = []
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
            )
            .execute()
        )
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def list_pdfs(folder_id: str, recursive: bool = False) -> list[dict]:
    """
    List PDF files in a folder.
    Set recursive=True to scan subfolders too.
    """
    service = _build_service()
    return _list_pdfs_recursive(service, folder_id) if recursive else _list_pdfs_flat(service, folder_id)


def _list_pdfs_flat(service, folder_id: str) -> list[dict]:
    pdf_mimes = {"application/pdf", "application/vnd.google-apps.document"}
    all_files = list_files(folder_id)
    return [f for f in all_files if f["mimeType"] in pdf_mimes]


def _list_pdfs_recursive(service, folder_id: str) -> list[dict]:
    """List PDFs including subfolders (from gdrive_eee.py pattern)."""
    results = []

    # PDFs in this folder
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            orderBy="name",
        ).execute()
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    # Recurse into subfolders
    sub_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    page_token = None
    subfolders = []
    while True:
        response = service.files().list(
            q=sub_query,
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
        ).execute()
        subfolders.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    for sub in subfolders:
        results.extend(_list_pdfs_recursive(service, sub["id"]))

    return results


def stream_pdf(file_id: str) -> bytes:
    """Download a Drive file and return raw bytes (no local file saved)."""
    service = _build_service()
    file_meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
    mime = file_meta.get("mimeType", "")

    buffer = io.BytesIO()

    if mime == "application/vnd.google-apps.document":
        request = service.files().export_media(fileId=file_id, mimeType="application/pdf")
    else:
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()
