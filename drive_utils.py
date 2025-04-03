# drive_utils.py
import pandas as pd
import io
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import tempfile
import json
import streamlit as st

# Authenticate Google Drive using only Streamlit Cloud secrets

def authenticate_drive():
    try:
        if "client_secrets_json" not in st.secrets:
            raise ValueError("'client_secrets_json' not found in Streamlit secrets.")

        secrets_json = st.secrets["client_secrets_json"].strip()
        if not secrets_json:
            raise ValueError("Streamlit secret 'client_secrets_json' is empty.")

        json.loads(secrets_json)  # Validate format
        with open("client_secrets.json", "w") as f:
            f.write(secrets_json)

    except Exception as e:
        st.error("❌ Google Drive authentication failed. Missing or invalid credentials.")
        raise e

    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

_drive_instance = None

def get_drive():
    global _drive_instance
    if _drive_instance is None:
        _drive_instance = authenticate_drive()
    return _drive_instance

def read_excel_from_drive(file_id):
    file = get_drive().CreateFile({'id': file_id})
    file.FetchMetadata()
    file.GetContentFile('temp.xlsx')
    return pd.read_excel('temp.xlsx', engine='openpyxl')

def read_csv_from_drive(file_id):
    file = get_drive().CreateFile({'id': file_id})
    file.FetchMetadata()
    file.GetContentFile('temp.csv')
    return pd.read_csv('temp.csv')

def write_df_to_drive(df, file_id, file_type="csv"):
    file = get_drive().CreateFile({'id': file_id})

    if file_type == "csv":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', encoding='utf-8') as tmp:
            df.to_csv(tmp.name, index=False)
            file.SetContentFile(tmp.name)
    elif file_type == "excel":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            file.SetContentFile(tmp.name)

    file.Upload()
