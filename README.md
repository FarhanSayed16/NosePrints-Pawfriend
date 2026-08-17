# 🐾 NosePrints × PawFriend

**AI-powered dog nose-print biometric identification for [PawFriend.in](https://pawfriend.in)**

Like human fingerprints, every dog's nose print is unique for life. NosePrints uses deep learning to register dogs by their nose print, reunite lost pets with owners, and identify found strays — all from a smartphone, no app install required.

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
