FROM python:3.11-slim

WORKDIR /app

ARG MODEL_WEIGHTS_URL="https://raw.githubusercontent.com/manumanoj0010/georoad-inspector/development/backend/models/road_damage_best.pt"

# Install system deps for OpenCV (required by ultralytics)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
RUN mkdir -p models \
    && curl -fL "$MODEL_WEIGHTS_URL" -o models/road_damage_best.pt

EXPOSE 7860

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]
