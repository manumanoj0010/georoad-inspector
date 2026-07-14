"""Phase 2 integration tests — inspection runs, image upload, EXIF extraction."""

import io
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import init_db, engine, Base


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
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_inspection_run(client):
    resp = await client.post(
        "/api/inspection-runs",
        json={"name": "Test Highway Inspection"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Highway Inspection"
    assert data["status"] == "created"
    assert data["total_images"] == 0
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_list_inspection_runs(client):
    # Create two runs
    await client.post("/api/inspection-runs", json={"name": "Run 1"})
    await client.post("/api/inspection-runs", json={"name": "Run 2"})

    resp = await client.get("/api/inspection-runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_inspection_run_not_found(client):
    resp = await client.get("/api/inspection-runs/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_inspection_run(client):
    create_resp = await client.post("/api/inspection-runs", json={"name": "Delete Me"})
    run_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/inspection-runs/{run_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/inspection-runs/{run_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_image(client, tmp_path):
    """Test uploading a valid JPEG image."""
    # Create the run
    create_resp = await client.post("/api/inspection-runs", json={"name": "Upload Test"})
    run_id = create_resp.json()["id"]

    # Create a minimal valid JPEG in memory
    from PIL import Image as PILImage

    img = PILImage.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    resp = await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("test_road.jpg", buf.getvalue(), "image/jpeg"))],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["uploaded"] == 1
    assert data["failed"] == 0
    assert len(data["images"]) == 1
    assert data["images"][0]["original_filename"] == "test_road.jpg"
    assert data["images"][0]["width"] == 100
    assert data["images"][0]["height"] == 100
    # No GPS in a synthetic image
    assert data["images"][0]["latitude"] is None
    assert data["images"][0]["location_method"] == "unmapped"


@pytest.mark.asyncio
async def test_upload_invalid_file(client):
    """Test that non-image files are rejected."""
    create_resp = await client.post("/api/inspection-runs", json={"name": "Invalid Test"})
    run_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("notes.txt", b"hello world", "text/plain"))],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["uploaded"] == 0
    assert data["failed"] == 1
    assert len(data["errors"]) == 1


@pytest.mark.asyncio
async def test_upload_with_gps_exif(client):
    """Test that GPS EXIF is extracted from a geotagged image."""
    # Use a sample image from the old project if available
    sample_dir = Path(__file__).parent.parent.parent.parent / "road-asset-detector" / "data" / "sample_images"
    sample_images = list(sample_dir.glob("*.jpg")) if sample_dir.exists() else []

    if not sample_images:
        pytest.skip("No sample geotagged images available")

    create_resp = await client.post("/api/inspection-runs", json={"name": "GPS Test"})
    run_id = create_resp.json()["id"]

    img_path = sample_images[0]
    content = img_path.read_bytes()

    resp = await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", (img_path.name, content, "image/jpeg"))],
    )
    data = resp.json()
    assert data["uploaded"] == 1
    img_data = data["images"][0]
    # These sample images have GPS embedded
    assert img_data["latitude"] is not None
    assert img_data["longitude"] is not None
    assert img_data["location_method"] == "camera_exif_approximation"
