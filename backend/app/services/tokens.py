"""Secure one-time token helpers for invites and password resets."""

from __future__ import annotations

import hashlib
import secrets


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
