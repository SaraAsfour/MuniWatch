"""
AES-256-GCM encryption/decryption for evidence clips stored as BYTEA
in TimescaleDB. Encryption happens once when go2rtc/the edge pipeline
saves a clip; decryption happens in memory, on demand, only when an
authenticated user taps "Play Decrypted Clip" — the plaintext video is
never written back to disk.
"""
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

# In production, derive/store this via a secrets manager (e.g. AWS KMS,
# HashiCorp Vault) — never hard-code it. Falling back to a value derived
# from JWT_SECRET_KEY here only so the project runs out-of-the-box in dev.
_KEY_MATERIAL = (settings.JWT_SECRET_KEY.encode("utf-8") * 2)[:32]


def encrypt_clip(plaintext_bytes: bytes) -> tuple[bytes, bytes]:
    """Returns (ciphertext, nonce) — both get stored in the DB row."""
    aesgcm = AESGCM(_KEY_MATERIAL)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, associated_data=None)
    return ciphertext, nonce


def decrypt_clip(ciphertext: bytes, nonce: bytes) -> bytes:
    aesgcm = AESGCM(_KEY_MATERIAL)
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
