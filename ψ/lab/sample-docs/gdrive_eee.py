#!/usr/bin/env python3
"""
Google Drive → eee Integration Script

Downloads PDFs from a Google Drive folder and processes them
with the agentic_pdf_processor (./eee pipeline).

Usage:
    python3 scripts/gdrive_eee.py FOLDER_ID
    python3 scripts/gdrive_eee.py FOLDER_ID --download-dir ./my_pdfs
    python3 scripts/gdrive_eee.py FOLDER_ID --skip-existing

First run will open a browser for Google OAuth consent.
Token is cached in scripts/token.json for subsequent runs.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

SCRIPT_DIR = Path(__file__).parent.resolve()
CREDENTIALS_FILE = SCRIPT_DIR / 'credentials.json'
TOKEN_FILE = SCRIPT_DIR / 'token.json'
PROJECT_ROOT = SCRIPT_DIR.parent


def authenticate():
    """Authenticate with Google Drive API using OAuth2."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("❌ Error: credentials.json not found!")
                print(f"   Expected at: {CREDENTIALS_FILE}")
                print()
                print("📋 Setup Instructions:")
                print("   1. Go to https://console.cloud.google.com")
                print("   2. Create/select a project")
                print("   3. Enable 'Google Drive API'")
                print("   4. Go to Credentials → Create OAuth 2.0 Client ID (Desktop)")
                print("   5. Download credentials.json → place in scripts/ folder")
                sys.exit(1)

            print("🔐 Opening browser for Google authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print("✅ Authentication successful! Token saved.")

    return creds


def list_pdfs_in_folder(service, folder_id, recursive=True):
    """List all PDF files in a Google Drive folder (optionally recursive)."""
    results = []

    # First, get direct PDFs
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, size)',
            pageToken=page_token,
            orderBy='name'
        ).execute()
        results.extend(response.get('files', []))
        page_token = response.get('nextPageToken')
        if not page_token:
            break

    # Then, recurse into subfolders
    if recursive:
        subfolder_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        page_token = None
        subfolders = []
        while True:
            response = service.files().list(
                q=subfolder_query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token,
                orderBy='name'
            ).execute()
            subfolders.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break

        for subfolder in subfolders:
            print(f"   📁 Scanning subfolder: {subfolder['name']}/")
            sub_results = list_pdfs_in_folder(service, subfolder['id'], recursive=True)
            results.extend(sub_results)

    return results


def download_file(service, file_id, file_name, download_dir):
    """Download a file from Google Drive."""
    filepath = download_dir / file_name

    if filepath.exists():
        print(f"   ⏭️  Already downloaded: {file_name}")
        return filepath

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   ⬇️  Downloading: {pct}%", end='\r')

    filepath.write_bytes(fh.getvalue())
    print(f"   ✅ Downloaded: {file_name} ({len(fh.getvalue()) / 1024 / 1024:.1f} MB)")
    return filepath


def get_existing_outputs(output_dir):
    """Get set of basenames (without extension) of already-processed files."""
    existing = set()
    if output_dir.exists():
        for f in output_dir.glob('*.md'):
            existing.add(f.stem)
    return existing


def run_eee(filepath, file_id=None):
    """Run the agentic_pdf_processor directly on a file, passing file_id if available."""
    processor = PROJECT_ROOT / 'scripts' / 'agentic_pdf_processor.py'
    cmd = ['python3', str(processor), str(filepath)]
    if file_id:
        cmd.extend(['--file-id', file_id])
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=False
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description='Download PDFs from Google Drive and process with ./eee')
    parser.add_argument('folder_id', help='Google Drive Folder ID')
    parser.add_argument('--download-dir', default='downloaded_pdfs',
                        help='Local directory to download PDFs to (default: downloaded_pdfs)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip files that already have .md output in references/rulings_committee/')
    parser.add_argument('--list-only', action='store_true',
                        help='Only list files in the folder, do not download or process')
    parser.add_argument('--download-only', action='store_true',
                        help='Only download files, do not process with ./eee')

    args = parser.parse_args()

    # Setup
    download_dir = Path(args.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    output_dir = PROJECT_ROOT / 'references' / 'rulings_committee'

    # Authenticate
    print("=" * 60)
    print("🚀 Google Drive → eee Integration")
    print("=" * 60)
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # List files
    print(f"\n📂 Listing PDFs in folder: {args.folder_id}")
    files = list_pdfs_in_folder(service, args.folder_id)

    if not files:
        print("   ❌ No PDF files found in this folder.")
        print("   💡 Make sure the Folder ID is correct.")
        print("   💡 Folder ID is the last part of the Google Drive URL:")
        print("      https://drive.google.com/drive/folders/FOLDER_ID_HERE")
        sys.exit(1)

    print(f"   📄 Found {len(files)} PDF files\n")

    # Get existing outputs for skip logic
    existing = get_existing_outputs(output_dir) if args.skip_existing else set()

    # List only mode
    if args.list_only:
        for i, f in enumerate(files, 1):
            size_mb = int(f.get('size', 0)) / 1024 / 1024
            status = "✅ processed" if f['name'].replace('.pdf', '') in existing else "⬜ pending"
            print(f"   {i:3d}. [{status}] {f['name']} ({size_mb:.1f} MB)")
        print(f"\n   Total: {len(files)} files")
        return

    # Process each file
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, f in enumerate(files, 1):
        file_name = f['name']
        file_stem = file_name.replace('.pdf', '').replace('.PDF', '')

        # Skip if already processed
        if args.skip_existing and file_stem in existing:
            print(f"\n[{i}/{len(files)}] ⏭️  Skipping (already processed): {file_name}")
            skip_count += 1
            continue

        print(f"\n[{i}/{len(files)}] 📥 Processing: {file_name}")

        # Download
        filepath = download_file(service, f['id'], file_name, download_dir)

        if args.download_only:
            success_count += 1
            continue

        # Run eee with file_id
        print(f"   🤖 Running extraction...")
        if run_eee(filepath, file_id=f['id']):
            success_count += 1
        else:
            fail_count += 1
            print(f"   ❌ Failed to process: {file_name}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"   ✅ Success: {success_count}")
    print(f"   ⏭️  Skipped: {skip_count}")
    print(f"   ❌ Failed:  {fail_count}")
    print(f"   📁 Total:   {len(files)}")
    print("=" * 60)


if __name__ == '__main__':
    main()
