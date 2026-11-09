# Ops completion status — 10 Nov 2026 (updated after DB restore)

## Stack now

| Check | Result |
|-------|--------|
| `/health` | **`healthy`** · `database: connected` · `embedding_mode: real` |
| Frontend tunnel | `http://localhost:5173` (HTTP 200) · `npm run tunnel` |
| Strict demo | `MATCH_STRICT_DEMO=true` |
| Pytest | 50/50 |
| Local junk gates | Pass — `docs/OPS_ACCEPTANCE_API.json` |

## Registry purge (done)

Deleted **12** junk/incomplete dogs (including known **Jack** + all **0-print** rows).

**Kept (have nose prints):**

| Name | Prints |
|------|-------:|
| Max | 2 |
| Ness | 3 |

Re-run if needed:

```powershell
cd D:\NosePrints-Pawfriend
.\backend\venv\Scripts\python.exe scripts\ops_purge_registry.py --dry-run --junk-only --zero-prints
```

## Still on you (cannot finish from this PC alone)

1. **Phone HTTPS acceptance** — hard-refresh `https://noseprints.farhanbuilds.in`, then keyboard reject / real nose / look soft-warn  
2. **Cloud Run hosting** — needs `gcloud` + Docker Desktop running  
3. **Closed pilot** (≥10–20 real dogs) → then embedding fine-tune  

## Processes left running

- API: uvicorn on `:8000`  
- Frontend: vite preview tunnel on `:5173`  
