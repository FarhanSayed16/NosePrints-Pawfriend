# 🐾 NosePrints × PawFriend

**AI-powered dog nose-print biometric identification for [PawFriend.in](https://pawfriend.in)**

Like human fingerprints, every dog's nose print is unique for life. NosePrints uses deep learning to register dogs by their nose print, reunite lost pets with owners, and identify found strays — all from a smartphone, no app install required.

**v1 scope:** nose-print ID only. Retina/iris scanning is out. Native apps are later.

**Plan & status:** [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) · [`docs/task.md`](docs/task.md) · [`docs/STAFF_SOP.md`](docs/STAFF_SOP.md) · [`docs/ACCURACY.md`](docs/ACCURACY.md) · **[`docs/DEPLOY.md`](docs/DEPLOY.md) (free standalone hosting)**.

### Staff login (Phase 0)
Owner phone/email is staff-only. Create the first admin once, then log in:

```bash
# First staff user (only works on an empty staff table)
curl -X POST http://localhost:8000/api/v1/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"staff@pawfriend.in\",\"password\":\"choose-a-long-password\"}"

# Later logins
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"staff@pawfriend.in\",\"password\":\"choose-a-long-password\"}"
```

Use the returned `access_token` as `Authorization: Bearer <token>` on `/api/v1/owners/` and `/api/v1/match/confirm`, or open **`/staff`** in the PWA to review the match queue.

When `DEBUG=false`, identify/upload return **503** until a real `embedding_model.onnx` is present. Do not use the example JWT secret in production.

### Train the nose detector (Phase 1)
Use **Python 3.12** (not 3.14 — PyTorch CUDA wheels are not ready there). Dataset path: `ml/data/detector/dog_nose_yolov8/`.

```bash
py -3.12 -m venv ml\.venv
ml\.venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install -r ml/requirements.txt
cd ml/training
python train_detector.py --epochs 40 --batch 8 --imgsz 640 --device 0
```

This writes `backend/models/nose_detector.onnx`. Restart the FastAPI server afterward. Upload/identify now **reject** photos if no nose is found.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL + pgvector)

### 1. Start the Database
```bash
docker-compose up -d
```

### 2. Start the Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

---

## 📁 Project Structure

```
NosePrints-Pawfriend/
├── backend/                # FastAPI + Python
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   ├── config.py       # Environment config
│   │   ├── db.py           # Database sessions
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── routers/        # API endpoints
│   │   └── services/       # ML inference, matching, storage
│   └── requirements.txt
├── frontend/               # React PWA (Vite)
│   └── src/
│       ├── components/     # CameraCapture, Navbar
│       ├── pages/          # Home, Register, Identify, Directory, LostDogs
│       └── services/       # API client
├── ml/                     # ML training pipeline
│   └── training/
│       ├── train_embedding.py  # ResNet50 + ArcFace
│       ├── evaluate.py         # ROC curve + AUC
│       ├── export_onnx.py      # PyTorch → ONNX
│       └── augmentations.py    # Data augmentation
├── docs/                   # Project documentation
├── docker-compose.yml      # PostgreSQL + pgvector
└── .env.example            # Environment template
```

---

## 🧠 How It Works

1. **Nose Detection** — YOLOv8-nano localizes the nose region
2. **Quality Gate** — Checks sharpness, brightness, and framing
3. **Embedding Extraction** — ResNet50 produces a 512-d "nose fingerprint"
4. **Vector Search** — pgvector cosine similarity finds the closest match
5. **Human Confirmation** — Staff reviews before releasing owner info

---

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React PWA (Vite) |
| Backend | FastAPI (Python) |
| ML Inference | ONNX Runtime |
| ML Training | PyTorch + ArcFace |
| Database | PostgreSQL + pgvector |
| Storage | S3-compatible / Local |

---

## 📝 License

Built for PawFriend.in 🐾
