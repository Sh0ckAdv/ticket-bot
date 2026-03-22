import os
from dotenv import load_dotenv

load_dotenv()


def get_discord_token() -> str:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError("DISCORD_TOKEN lipsește din fișierul .env.")
    return token


def get_guild_id() -> int | None:
    raw_value = os.getenv("GUILD_ID", "").strip()
    if not raw_value:
        return None

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("GUILD_ID trebuie să fie un număr valid.") from exc


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL lipsește din fișierul .env.")
    return database_url