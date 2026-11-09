"""
Staff registry purge when Supabase is reachable.
Usage:
  backend\\venv\\Scripts\\python.exe scripts\\ops_purge_registry.py --dry-run
  backend\\venv\\Scripts\\python.exe scripts\\ops_purge_registry.py --junk-only
  backend\\venv\\Scripts\\python.exe scripts\\ops_purge_registry.py --all   # full demo wipe
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

BASE = os.getenv("OPS_API_BASE", "http://127.0.0.1:8000")
EMAIL = os.getenv("STAFF_BOOTSTRAP_EMAIL", "")
PASSWORD = os.getenv("STAFF_BOOTSTRAP_PASSWORD", "")

JUNK_NAME_HINTS = (
    "jack",
    "keyboard",
    "test",
    "junk",
    "demo",
    "asdf",
    "abc",
    "sample",
    "fake",
    "wall",
    "floor",
    "hh",
    "tg",
)


def _api_paths(client: httpx.Client) -> dict[str, str]:
    paths = list(client.get(f"{BASE}/openapi.json").json().get("paths", {}))
    login = next(p for p in paths if p.endswith("/auth/login"))
    dogs = next(p for p in paths if p.rstrip("/").endswith("/dogs") and "{" not in p)
    return {"login": login, "dogs": dogs.rstrip("/") + "/"}


def login(client: httpx.Client, login_path: str) -> str:
    r = client.post(f"{BASE}{login_path}", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def list_all_dogs(client: httpx.Client, dogs_path: str) -> list[dict]:
    dogs: list[dict] = []
    page = 1
    while True:
        r = client.get(f"{BASE}{dogs_path}", params={"page": page, "per_page": 100})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        dogs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return dogs


def is_junk(dog: dict, *, zero_prints: bool = False) -> bool:
    name = (dog.get("name") or "").strip().lower()
    prints = int(dog.get("nose_print_count") or 0)
    if any(h == name or h in name for h in JUNK_NAME_HINTS):
        return True
    if not name or name in {"unknown", "n/a", "na", "dog"}:
        return True
    if zero_prints and prints == 0:
        return True
    # no nose prints and no look photo → likely incomplete junk
    if prints == 0 and not dog.get("profile_photo_url"):
        return True
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--junk-only", action="store_true")
    p.add_argument(
        "--zero-prints",
        action="store_true",
        help="Also delete dogs with 0 nose prints (incomplete demo rows)",
    )
    p.add_argument("--all", action="store_true", help="Delete every dog (demo wipe)")
    args = p.parse_args()
    if not args.junk_only and not args.all:
        args.junk_only = True

    if not EMAIL or not PASSWORD:
        print("Missing STAFF_BOOTSTRAP_EMAIL/PASSWORD in backend/.env", file=sys.stderr)
        return 2

    try:
        with httpx.Client(timeout=60.0) as client:
            # health
            h = client.get(f"{BASE}/health")
            health = h.json()
            print("health", health.get("status"), "db=", health.get("database"))
            if health.get("database") != "connected":
                print(
                    "BLOCKED: database not connected. Fix Supabase DATABASE_URL then re-run.",
                    file=sys.stderr,
                )
                return 3
            api = _api_paths(client)
            token = login(client, api["login"])
            client.headers["Authorization"] = f"Bearer {token}"
            dogs = list_all_dogs(client, api["dogs"])
            print(f"registry_count={len(dogs)}")
            if args.all:
                targets = dogs
                mode = "all"
            else:
                targets = [d for d in dogs if is_junk(d, zero_prints=args.zero_prints)]
                mode = "junk-only" + ("+zero-prints" if args.zero_prints else "")
            print(f"delete_targets={len(targets)} mode={mode}")
            dogs_base = api["dogs"].rstrip("/")
            for d in targets:
                label = f"{d.get('name')} ({d.get('id')}) prints={d.get('nose_print_count')}"
                if args.dry_run:
                    print("DRY", label)
                    continue
                r = client.delete(f"{BASE}{dogs_base}/{d['id']}")
                print(("OK" if r.status_code in (200, 204) else f"FAIL {r.status_code}"), label)
            return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
