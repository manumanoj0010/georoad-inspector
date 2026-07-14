# GeoRoad Inspector — Architecture

## Overview

GeoRoad Inspector uses a split architecture to keep hosting costs predictable while providing full AI-powered road damage detection with live inference.

The memory-intensive YOLO inference runs on a Hugging Face Docker Space, while the lightweight API, database, and review workflow run on Render.

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
        HFS["YOLO Inference Service<br/>(FastAPI on Docker Space)<br/>CPU/GPU hardware options"]
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

## Component Details

| Component | Platform | Cost | RAM | Purpose |
|-----------|----------|------|-----|---------|
| Frontend | Render Static | $0 | CDN | React UI, Leaflet map |
| Backend API | Render Starter | $7/mo | 512MB | REST API, DB, uploads, EXIF, review, GeoJSON, ArcGIS publish |
| Persistent Disk | Render | $0.25/mo | 1GB | Image storage + SQLite |
| YOLO Inference | HF Docker Space | Depends on HF plan/hardware | Varies | Model loading and detection |
| GIS Layer | ArcGIS Online | $0* | — | Hosted feature layer for confirmed detections |

**Render cost remains ~$7.25/month. Add Hugging Face plan/hardware costs as selected.**

## Inference Modes

The backend supports two inference modes controlled by the `INFERENCE_SERVICE_URL` environment variable:

### Remote Mode (Production / Render)
When `INFERENCE_SERVICE_URL` is set, the backend sends images to the Hugging Face Docker Space inference service via HTTP. This keeps the Render instance lightweight (no PyTorch/YOLO in memory).

```
INFERENCE_SERVICE_URL=https://<your-space-subdomain>.hf.space
```

### Local Mode (Development)
When `INFERENCE_SERVICE_URL` is not set, the backend loads the YOLO model directly. This requires sufficient RAM and is intended for local development only.

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

## Environment Variables

### Render Backend (georoad-inspector-api)
| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./georoad.db` | Database connection |
| `UPLOAD_DIR` | `/opt/render/project/data/uploads` | Persistent image storage |
| `INFERENCE_SERVICE_URL` | `https://<space>.hf.space` | Hugging Face inference endpoint |
| `APP_ENV` | `production` | Environment mode |
| `CORS_ORIGINS` | `https://georoad-inspector-ui.onrender.com` | Allowed CORS origins |
| `ARCGIS_PORTAL_URL` | `https://www.arcgis.com` | ArcGIS portal |
| `ARCGIS_CLIENT_ID` | *(set in Render)* | OAuth client ID |
| `ARCGIS_CLIENT_SECRET` | *(set in Render)* | OAuth client secret |
| `ARCGIS_FEATURE_LAYER_URL` | *(set in Render)* | Target feature layer |

### Hugging Face Docker Space (inference-service)
No service secrets are required by default. The model weights are bundled in the image.

## Hugging Face Deployment

### Prerequisites
- Hugging Face account
- Docker Spaces access on your plan

### Deploy Steps

```bash
# Copy model weights into inference-service before publishing
mkdir -p inference-service/models
cp backend/models/road_damage_best.pt inference-service/models/

# Push inference-service files to your Hugging Face Docker Space repository
# Then wait for Space build to finish and get URL:
# https://<space-subdomain>.hf.space

# Set this URL as INFERENCE_SERVICE_URL in Render backend
```
