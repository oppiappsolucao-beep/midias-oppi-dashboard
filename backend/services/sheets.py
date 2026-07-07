import json
import os

import gspread
from google.oauth2.service_account import Credentials

from config import SCOPES, SHEET_ID

_worksheet = None


def get_google_creds_dict() -> dict:
    google_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if google_json:
        return json.loads(google_json)

    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")

    env_creds = {
        "type": os.getenv("GOOGLE_TYPE", "service_account"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID", ""),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", ""),
        "private_key": private_key,
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL", ""),
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": os.getenv(
            "GOOGLE_AUTH_PROVIDER_X509_CERT_URL",
            "https://www.googleapis.com/oauth2/v1/certs",
        ),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL", ""),
        "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN", "googleapis.com"),
    }

    required = ["project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing = [field for field in required if not env_creds.get(field)]
    if missing:
        raise ValueError(
            "Credenciais Google ausentes. "
            f"Campos faltando: {', '.join(missing)}"
        )

    return env_creds


def connect_sheet():
    global _worksheet
    if _worksheet is not None:
        return _worksheet

    creds_dict = get_google_creds_dict()
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    _worksheet = sheet.get_worksheet(0)
    return _worksheet


def fetch_sheet_rows() -> list[list[str]]:
    worksheet = connect_sheet()
    return worksheet.get_all_values()


def update_sheet_cell(row_index: int, col: int, value: str) -> None:
    worksheet = connect_sheet()
    worksheet.update_cell(row_index + 2, col, value)
