from __future__ import annotations

import secrets


AUTO_TOKEN = "auto"


def generate_token() -> str:
    return secrets.token_hex(32)


def normalize_token(value: object) -> str:
    if value is None:
        return generate_token()

    token = str(value).strip()
    if not token or token == AUTO_TOKEN:
        return generate_token()

    return token
