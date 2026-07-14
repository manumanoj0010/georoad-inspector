---
title: GeoRoad YOLO Inference
emoji: 🚧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# GeoRoad YOLO Inference

Docker Space for road damage detection used by GeoRoad Inspector backend.

## Endpoints

- GET /health
- POST /detect

## Build Notes

- The Docker image expects YOLO weights at models/road_damage_best.pt.
- If missing, /health returns model_loaded=false and /detect returns an error.

## Local Test (optional)

```bash
docker build -t georoad-inference .
docker run -p 7860:7860 georoad-inference
curl http://localhost:7860/health
```
