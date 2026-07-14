"""Phase 3 integration tests — YOLO inference, detection storage, processing."""

import io
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image as PILImage

from app.main import app
from app.database import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create fresh tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_test_jpeg() -> bytes:
    """Create a minimal JPEG image in memory."""
    img = PILImage.new("RGB", (640, 640), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _get_sample_image() -> bytes | None:
    """Try to load a real road damage image from the old project."""
    sample_dir = Path(__file__).parent.parent.parent.parent / "road-asset-detector" / "data" / "sample_images"
    samples = list(sample_dir.glob("*.jpg")) if sample_dir.exists() else []
    if samples:
        return samples[0].read_bytes()
    return None


@pytest.mark.asyncio
async def test_process_run_no_images(client):
    """Processing with no images should return 400."""
    resp = await client.post("/api/inspection-runs", json={"name": "Empty Run"})
    run_id = resp.json()["id"]

    resp = await client.post(f"/api/inspection-runs/{run_id}/process")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_process_run_with_image(client):
    """Full pipeline: upload image → process → get detections."""
    # Use real road image if available, otherwise synthetic
    image_data = _get_sample_image() or _make_test_jpeg()

    # Create run
    resp = await client.post("/api/inspection-runs", json={"name": "Process Test"})
    run_id = resp.json()["id"]

    # Upload image
    resp = await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("road_test.jpg", image_data, "image/jpeg"))],
    )
    assert resp.json()["uploaded"] == 1

    # Process
    resp = await client.post(f"/api/inspection-runs/{run_id}/process")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["processed"] == 1
    assert data["failed"] == 0
    assert "detections" in data
    assert "model_version" in data

    # Check status endpoint
    resp = await client.get(f"/api/inspection-runs/{run_id}/status")
    assert resp.status_code == 200
    status = resp.json()
    assert status["status"] == "completed"
    assert status["processed_images"] == 1

    # List detections
    resp = await client.get(f"/api/inspection-runs/{run_id}/detections")
    assert resp.status_code == 200
    detections = resp.json()
    # With real images we get detections, with synthetic possibly zero
    assert isinstance(detections, list)

    if detections:
        det = detections[0]
        assert "detection_id" in det
        assert det["detection_id"].startswith("RD-")
        assert "damage_type" in det
        assert "confidence" in det
        assert "x_min" in det
        assert "review_status" in det
        assert det["review_status"] == "unreviewed"


@pytest.mark.asyncio
async def test_detection_review_flow(client):
    """Test confirming and rejecting detections."""
    image_data = _get_sample_image()
    if not image_data:
        pytest.skip("No sample road images available for detection review test")

    # Create, upload, process
    resp = await client.post("/api/inspection-runs", json={"name": "Review Test"})
    run_id = resp.json()["id"]

    await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("road.jpg", image_data, "image/jpeg"))],
    )
    await client.post(f"/api/inspection-runs/{run_id}/process")

    # Get detections
    resp = await client.get(f"/api/inspection-runs/{run_id}/detections")
    detections = resp.json()

    if not detections:
        pytest.skip("No detections found in sample image")

    det_id = detections[0]["id"]

    # Confirm
    resp = await client.post(f"/api/detections/{det_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "confirmed"

    # Reject another if available
    if len(detections) > 1:
        det_id_2 = detections[1]["id"]
        resp = await client.post(f"/api/detections/{det_id_2}/reject")
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "rejected"


@pytest.mark.asyncio
async def test_detection_filtering(client):
    """Test filtering detections by confidence and status."""
    image_data = _get_sample_image()
    if not image_data:
        pytest.skip("No sample images for filter test")

    resp = await client.post("/api/inspection-runs", json={"name": "Filter Test"})
    run_id = resp.json()["id"]

    await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("road.jpg", image_data, "image/jpeg"))],
    )
    await client.post(f"/api/inspection-runs/{run_id}/process")

    # Filter by min confidence
    resp = await client.get(
        f"/api/inspection-runs/{run_id}/detections",
        params={"min_confidence": 0.5},
    )
    assert resp.status_code == 200
    high_conf = resp.json()

    resp = await client.get(
        f"/api/inspection-runs/{run_id}/detections",
        params={"min_confidence": 0.01},
    )
    all_dets = resp.json()

    # High-confidence subset should be <= total
    assert len(high_conf) <= len(all_dets)
