# GeoRoad Inspector

> AI-powered roadway inspection — detects road damage from street-level images, maps detections to GPS coordinates, and publishes structured GIS data to ArcGIS Online.

**Built by [Manoj Boddu](https://www.linkedin.com/in/manumanoj0010/) · [Source Code](https://github.com/manumanoj0010/georoad-inspector)**

---

## System Architecture

```mermaid
graph TB
    subgraph "User Browser"
        FE["React Frontend<br/>(Render Static Site - FREE)"]
    end

    subgraph "Render - $7.25/mo"
        API["FastAPI Backend<br/>(Render Starter - $7/mo)<br/>512MB RAM"]
        DISK["Persistent Disk<br/>($0.25/mo - 1GB)<br/>Uploads + SQLite DB"]
        API --- DISK
    end

    subgraph "Hugging Face Spaces"
        HFS["YOLO Inference Service<br/>(FastAPI on Docker Space)"]
        MODEL["YOLOv8 Model<br/>road_damage_best.pt"]
        HFS --- MODEL
    end

    subgraph "ArcGIS Online"
        ARCGIS["Hosted Feature Layer<br/>(Point geometry, WGS84)"]
    end

    FE -->|"Upload images<br/>Review detections<br/>View map"| API
    API -->|"Send image bytes<br/>for inference"| HFS
    HFS -->|"Return bounding boxes<br/>+ classifications"| API
    API -->|"Publish confirmed<br/>detections (OAuth)"| ARCGIS
```

## Request Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as Frontend (Render Static)
    participant API as Backend API (Render $7)
    participant HFS as YOLO Service (HF Docker Space)
    participant AG as ArcGIS Online

    Note over U,AG: 1. Upload Images
    U->>FE: Drag & drop images
    FE->>API: POST /api/runs/{id}/images
    API->>API: Extract EXIF GPS, store to disk

    Note over U,AG: 2. Process (Inference)
    FE->>API: POST /api/runs/{id}/process
    loop Each image
        API->>HFS: POST /detect (image bytes)
        HFS->>HFS: YOLO inference
        HFS-->>API: Bounding boxes + labels + confidence
    end
    API->>API: Create Detection records in SQLite

    Note over U,AG: 3. Review & Map
    FE->>API: GET /api/runs/{id}/detections
    API-->>FE: Detection list with GPS
    U->>FE: Confirm/Reject detections
    FE->>API: POST /api/detections/{id}/confirm

    Note over U,AG: 4. Publish to ArcGIS
    FE->>API: POST /api/runs/{id}/publish/arcgis
    API->>AG: OAuth token + addFeatures
    AG-->>API: objectIds
    API-->>FE: Published count
```

## Deployment Cost Breakdown

| Component | Platform | Cost | RAM | Purpose |
|-----------|----------|------|-----|---------|
| Frontend | Render Static | $0 | CDN | React UI, Leaflet map |
| Backend API | Render Starter | $7/mo | 512MB | REST API, DB, uploads, EXIF, review, GeoJSON, ArcGIS publish |
| Persistent Disk | Render | $0.25/mo | 1GB | Image storage + SQLite |
| YOLO Inference | HF Docker Space | Varies by plan | Varies | Model loading and detection |
| GIS Layer | ArcGIS Online | $0* | — | Hosted feature layer for confirmed detections |

**Total Render cost: ~$7.25/month with full live inference**

## Deployment Topology

```mermaid
graph LR
    subgraph "GitHub Repo"
        CODE["georoad-inspector"]
    end

    CODE -->|"auto-deploy<br/>render.yaml"| RENDER["Render<br/>(API + Static)"]
    CODE -->|"push to HF Space repo<br/>inference-service/"| HFS["Hugging Face Docker Space<br/>(Inference)"]

    RENDER -->|"INFERENCE_SERVICE_URL"| HFS
```

## Features

- **Multi-image upload** with drag-and-drop, validation, and EXIF GPS extraction
- **YOLO road damage detection** — fine-tuned model detects potholes, longitudinal cracks, transverse cracks, alligator cracks
- **Interactive Leaflet map** with color-coded markers, popups, and filtering
- **Detection review workflow** — confirm, reject, or flag detections with audit trail
- **GeoJSON export** — standards-compliant FeatureCollection with proper [lon, lat] coordinate order
- **ArcGIS Online publishing** — push confirmed detections to hosted feature layers
- **Dashboard** with summary stats, damage type breakdown, and review progress
- **Demo mode** — preloaded data for immediate demonstration without GPU

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Leaflet |
| Backend | Python, FastAPI, SQLAlchemy (async), Pydantic |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ML Model | YOLOv8 (ultralytics), fine-tuned on RDD2022 |
| GIS | GeoJSON, ArcGIS REST API, Leaflet.js |
| Deployment | Docker, Docker Compose, nginx |

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy alembic pydantic pydantic-settings \
    python-multipart pillow exifread ultralytics geojson aiosqlite httpx greenlet

# Copy environment config
cp ../.env.example .env

# Seed demo data (optional — creates a pre-processed inspection run)
python -m app.seed_demo

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the frontend proxies API requests to the backend.

### Docker Compose

```bash
docker compose up --build
```

Open http://localhost:3000

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./georoad.db` | Database connection string |
| `UPLOAD_DIR` | `./uploads` | Image storage directory |
| `MODEL_WEIGHTS_PATH` | `./models/road_damage_best.pt` | YOLO model weights |
| `DEFAULT_CONFIDENCE_THRESHOLD` | `0.25` | Minimum detection confidence |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `ARCGIS_PORTAL_URL` | _(empty)_ | ArcGIS Online portal URL |
| `ARCGIS_CLIENT_ID` | _(empty)_ | ArcGIS OAuth client ID |
| `ARCGIS_CLIENT_SECRET` | _(empty)_ | ArcGIS OAuth client secret |
| `ARCGIS_FEATURE_LAYER_URL` | _(empty)_ | Target feature layer endpoint |

## API Documentation

Start the backend and visit http://localhost:8000/docs for interactive Swagger UI.

### Key Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/inspection-runs` | Create inspection |
| `POST` | `/api/inspection-runs/{id}/images` | Upload images |
| `POST` | `/api/inspection-runs/{id}/process` | Run YOLO detection |
| `GET` | `/api/inspection-runs/{id}/detections` | List detections (filterable) |
| `POST` | `/api/detections/{id}/confirm` | Confirm a detection |
| `POST` | `/api/detections/{id}/reject` | Reject a detection |
| `GET` | `/api/inspection-runs/{id}/geojson` | Get GeoJSON |
| `GET` | `/api/inspection-runs/{id}/geojson/download` | Download .geojson file |
| `POST` | `/api/inspection-runs/{id}/publish/arcgis` | Publish to ArcGIS |

### Detection Filters

`GET /api/inspection-runs/{id}/detections?damage_type=pothole&min_confidence=0.5&review_status=confirmed`

## GeoJSON Format

Output follows the GeoJSON specification (RFC 7946):

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "RD-2026-000001",
      "geometry": {
        "type": "Point",
        "coordinates": [-96.8961, 33.0198]
      },
      "properties": {
        "detectionId": "RD-2026-000001",
        "damageType": "pothole",
        "confidence": 0.91,
        "reviewStatus": "confirmed",
        "locationMethod": "camera_exif_approximation",
        "modelVersion": "road_damage_best"
      }
    }
  ]
}
```

## ArcGIS Configuration

1. Create a free [ArcGIS Developer account](https://developers.arcgis.com/sign-up/)
2. Register an OAuth application to get client_id and client_secret
3. Create a hosted feature layer with matching schema
4. Set environment variables:

```bash
ARCGIS_PORTAL_URL=https://www.arcgis.com
ARCGIS_CLIENT_ID=your_client_id
ARCGIS_CLIENT_SECRET=your_client_secret
ARCGIS_FEATURE_LAYER_URL=https://services.arcgis.com/.../FeatureServer/0
```

Without these variables, the app runs in **mock mode** — publishing succeeds locally without contacting ArcGIS.

## Database Schema

Six normalized tables: `inspection_runs`, `images`, `detections`, `review_actions`, `model_versions`, `arcgis_publications`.

## Model — Fine-tuning on RDD2022

### Overview

The detection model (`road_damage_best.pt`) is a **fine-tuned YOLOv8-nano** trained on the [RDD2022 dataset](https://github.com/sekilab/RoadDamageDetector), the largest publicly available multi-national road damage dataset released as part of the IEEE BigData Cup Challenge (CRDDC'2022).

---

### Dataset — RDD2022 (Road Damage Dataset 2022)

| Property | Details |
|----------|---------|
| **Full name** | RDD2022: Multi-national Road Damage Dataset |
| **Released by** | Arya et al., Sekimoto Lab, University of Tokyo |
| **Challenge** | CRDDC'2022 — IEEE Big Data Cup |
| **Countries** | Japan, India, Czech Republic, Norway, United States, China |
| **License** | CC BY-SA 4.0 |
| **Format** | JPEG images + Pascal VOC XML annotations |
| **Dataset source** | [FigShare](https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547) |

**Damage classes (4):**

| Class ID | Code | Label |
|----------|------|-------|
| 0 | D00 | Longitudinal Crack |
| 1 | D10 | Transverse Crack |
| 2 | D20 | Alligator Crack |
| 3 | D40 | Pothole |

---

### Base Model — YOLOv8-nano

| Property | Value |
|----------|-------|
| **Architecture** | YOLOv8-nano (`yolov8n.pt`) |
| **Framework** | Ultralytics v8.4.95 |
| **Type** | Single-stage object detection |
| **Parameters** | ~3.2M (nano variant) |
| **Pre-training** | COCO dataset (80 classes, 118K images) |

YOLOv8-nano was chosen for deployment efficiency — it runs on CPU (no GPU required) while maintaining competitive accuracy for road damage detection.

---

### Fine-tuning Configuration

| Hyperparameter | Value |
|----------------|-------|
| **Epochs** | 15 |
| **Image size** | 640 × 640 px |
| **Batch size** | 16 |
| **Optimizer** | Auto (AdamW) |
| **Pretrained weights** | `yolov8n.pt` (COCO) |
| **Task** | Detection |
| **Training date** | 2026-07-13 |
| **Framework version** | Ultralytics 8.4.95 |

**Train/Val split:**
Standard YOLO split from the RDD2022 `rdd2022.yaml` dataset config — typically **80% train / 20% val** as per the challenge default.

---

### Training Metrics (Validation Set)

| Metric | Value |
|--------|-------|
| **Precision** | 33.96% |
| **Recall** | 48.89% |
| **mAP@50** | 36.39% |
| **mAP@50-95** | 17.04% |

> **Note on metrics:** These numbers reflect a 15-epoch fine-tune on a challenging multi-national, multi-condition dataset with 4 damage classes. Road damage detection is inherently difficult (small objects, varied surfaces, weather, low contrast). Published CRDDC'2022 winner results using heavier YOLOv8 variants trained for 100+ epochs typically reach mAP@50 of 50–65%. This model prioritizes fast CPU inference for deployment, not maximum accuracy.

---

### How to Reproduce Training

1. Download RDD2022 from [FigShare](https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547)
2. Convert Pascal VOC XML annotations to YOLO format
3. Create a `rdd2022.yaml` dataset config pointing to your train/val directories and 4 classes
4. Run:

```bash
pip install ultralytics
yolo detect train \
  model=yolov8n.pt \
  data=rdd2022.yaml \
  epochs=15 \
  imgsz=640 \
  batch=16
```

5. Use `runs/detect/train/weights/best.pt` as `road_damage_best.pt`

---

### Dataset Citation

```bibtex
@article{arya2024rdd2022,
  title={RDD2022: A multi-national image dataset for automatic road damage detection},
  author={Arya, Deeksha and Maeda, Hiroya and Ghosh, Sanjay Kumar and Toshniwal, Durga and Sekimoto, Yoshihide},
  journal={Geoscience Data Journal},
  volume={11},
  number={4},
  pages={846--862},
  year={2024},
  publisher={Wiley Online Library}
}

@inproceedings{arya2022crowdsensing,
  title={Crowdsensing-based Road Damage Detection Challenge (CRDDC'2022)},
  author={Arya, Deeksha and others},
  booktitle={2022 IEEE International Conference on Big Data (Big Data)},
  pages={6378--6386},
  year={2022},
  organization={IEEE}
}
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

22 integration tests covering: image upload, EXIF extraction, YOLO inference, detection storage, review workflow, GeoJSON generation, coordinate order validation, ArcGIS publishing, and duplicate prevention.

## Known Limitations

- GPS coordinates represent the **camera location**, not the exact position of each detected defect
- Single images do not provide depth — no volume or dimension estimation
- Model accuracy depends on image quality, lighting, and road surface type
- The pretrained model covers 4 damage classes; additional classes require retraining
- ArcGIS publishing requires a properly configured hosted feature layer

## Project Structure

```
georoad-inspector/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Environment settings
│   │   ├── database.py             # SQLAlchemy async engine
│   │   ├── seed_demo.py            # Demo data seeder
│   │   ├── models/                 # ORM models (6 tables)
│   │   ├── schemas/                # Pydantic request/response types
│   │   ├── routers/                # API route handlers
│   │   ├── services/               # Business logic
│   │   │   ├── inference.py        # YOLO model management
│   │   │   ├── exif.py             # GPS/EXIF extraction
│   │   │   ├── processing.py       # Detection pipeline
│   │   │   ├── geojson.py          # GeoJSON generation
│   │   │   └── arcgis.py           # ArcGIS publishing
│   │   └── utils/                  # Validation, ID generation
│   ├── models/                     # YOLO weight files
│   └── tests/                      # Integration tests (22 tests)
└── frontend/
    ├── Dockerfile
    ├── src/
    │   ├── App.tsx                  # Main application
    │   ├── api/client.ts            # Typed API client
    │   ├── hooks/useInspection.ts   # State management
    │   ├── types/index.ts           # TypeScript interfaces
    │   └── components/
    │       ├── Dashboard.tsx        # Summary stats
    │       ├── ImageUpload.tsx      # Drag-and-drop upload
    │       ├── DetectionCard.tsx    # Bounding box + review
    │       ├── InspectionMap.tsx    # Leaflet map
    │       ├── FilterPanel.tsx      # Damage/confidence/status filters
    │       ├── ExportPanel.tsx      # GeoJSON download
    │       └── ArcGISPanel.tsx      # ArcGIS publish button
    └── nginx.conf                   # Production proxy config
```
