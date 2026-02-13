"""
Google Drive integration.
Authenticates via service account, lists files, streams PDF bytes.
All config from environment — no hardcoded paths.
"""
import io
import json
import os
from typing import Iterator

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config import GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_SCOPES


def _get_credentials() -> service_account.Credentials:
    """Build service account credentials from JSON string or file path."""
    sa_config = GOOGLE_SERVICE_ACCOUNT_JSON.strip()
    if not sa_config:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set. "
            "Set it to a JSON string or a path to the service account file."
        )

    if sa_config.startswith("{"):
        info = json.loads(sa_config)
    else:
        with open(sa_config) as f:
            info = json.load(f)

    return service_account.Credentials.from_service_account_info(
        info, scopes=GOOGLE_DRIVE_SCOPES
    )


def _build_service():
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


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


def stream_pdf(file_id: str) -> bytes:
    """
    Download a Drive file and return its raw bytes.
    Works for both native PDFs and Google Docs exported as PDF.
    """
    service = _build_service()
    file_meta = service.files().get(file_id=file_id, fields="mimeType,name").execute()
    mime = file_meta.get("mimeType", "")

    buffer = io.BytesIO()

    if mime == "application/vnd.google-apps.document":
        # Export Google Doc as PDF
        request = service.files().export_media(
            fileId=file_id, mimeType="application/pdf"
        )
    else:
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()


def list_pdfs(folder_id: str) -> list[dict]:
    """Convenience: list only PDF files (and Google Docs)."""
    all_files = list_files(folder_id)
    pdf_mimes = {
        "application/pdf",
        "application/vnd.google-apps.document",
    }
    return [f for f in all_files if f["mimeType"] in pdf_mimes]
