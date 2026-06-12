import base64

_SALT = b"ProfTracker-v1.3"
_ENC_GROQ = b"NwEEOR8UJChfJwhpA19hXTcDBxE2By0xPCIWVBQCaGoHRBs2H0RVEQldJHU7fW1lIjAuUmMqJBk="


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def get_groq_key() -> str:
    return _xor(base64.b64decode(_ENC_GROQ), _SALT).decode()
