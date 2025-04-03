# drive_utils.py (refactored for service account authentication)
import pandas as pd
import io
import os
import json
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "service_account.json"

_drive_service = None

def authenticate_drive():
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    try:
        if "gdrive_service_account" not in st.secrets:
            raise ValueError("❌ 'gdrive_service_account' not found in Streamlit secrets.")

        service_account_info = json.loads(st.secrets["gdrive_service_account"])
        with open(SERVICE_ACCOUNT_FILE, "w") as f:
            json.dump(service_account_info, f)

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        _drive_service = build("drive", "v3", credentials=creds)
        return _drive_service

    except Exception as e:
        st.error("❌ Google Drive service account authentication failed.")
        raise e

def read_excel_from_drive(file_id):
    service = authenticate_drive()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_excel(fh, engine='openpyxl')

def read_csv_from_drive(file_id):
    service = authenticate_drive()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)

def write_df_to_drive(df, file_id, file_type="csv"):
    service = authenticate_drive()

    if file_type == "csv":
        tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        df.to_csv(tmp_path, index=False)
        mime_type = "text/csv"
    elif file_type == "excel":
        tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
        with pd.ExcelWriter(tmp_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise ValueError("Unsupported file type")

    media = MediaFileUpload(tmp_path, mimetype=mime_type, resumable=False)

    try:
        service.files().update(fileId=file_id, media_body=media, body={}).execute()
    except Exception as e:
        st.error(f"❌ Failed to upload to Google Drive: {e}")
        raise e
    finally:
        os.remove(tmp_path)
