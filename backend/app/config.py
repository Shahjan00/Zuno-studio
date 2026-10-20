"""Environment-backed application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV_FILE)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://zuno:replace_with_a_local_password@localhost:5432/zuno",
)
