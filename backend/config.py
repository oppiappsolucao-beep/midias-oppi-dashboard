import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "logo-oppi.png"
if not LOGO_PATH.exists():
    LOGO_PATH = BASE_DIR / "LOGOS.png"

SHEET_ID = os.getenv("SHEET_ID", "16l701e6FdfkXYQrCxknZRidTonR3f80SQcUq3tGNw5I")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

APP_USER = os.getenv("APP_USER", "operacao")
APP_PASS = os.getenv("APP_PASS", "100316*")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]

MESES_ORDEM = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

EXPECTED_MEDIA_HEADERS = [
    "Mês",
    "Semana",
    "Empresa",
    "Tema",
    "Valor",
    "Status Pagamento",
    "Tipo de arte",
    "Status da arte",
    "Data Publicação",
]

SHEET_COL_TEMA = 4
SHEET_COL_STATUS_ARTE = 8
