"""Phase 7 tests — ArcGIS publishing (mock mode), duplicate prevention."""

import io
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
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


def _get_sample_image() -> bytes | None:
    sample_dir = Path(__file__).parent.parent.parent.parent / "road-asset-detector" / "data" / "sample_images"
    samples = list(sample_dir.glob("*.jpg")) if sample_dir.exists() else []
    return samples[0].read_bytes() if samples else None


async def _setup_confirmed_detections(client: AsyncClient) -> int | None:
    """Create run, upload, process, confirm all detections. Return run_id."""
    image_data = _get_sample_image()
    if not image_data:
        return None

    resp = await client.post("/api/inspection-runs", json={"name": "ArcGIS Test"})
    run_id = resp.json()["id"]

    await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("road.jpg", image_data, "image/jpeg"))],
    )
    await client.post(f"/api/inspection-runs/{run_id}/process")

    # Confirm all detections
    resp = await client.get(f"/api/inspection-runs/{run_id}/detections")
    for det in resp.json():
        await client.post(f"/api/detections/{det['id']}/confirm")

    return run_id


@pytest.mark.asyncio
async def test_publish_no_confirmed_detections(client):
    """Publishing with no confirmed detections should succeed with zero count."""
    image_data = _get_sample_image()
    if not image_data:
        pytest.skip("No sample images")

    resp = await client.post("/api/inspection-runs", json={"name": "No Confirm"})
    run_id = resp.json()["id"]

    await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("road.jpg", image_data, "image/jpeg"))],
    )
    await client.post(f"/api/inspection-runs/{run_id}/process")

    # Publish without confirming
    resp = await client.post(f"/api/inspection-runs/{run_id}/publish/arcgis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["published_count"] == 0


@pytest.mark.asyncio
async def test_publish_mock_mode(client):
    """When ArcGIS is not configured, mock mode should publish successfully."""
    run_id = await _setup_confirmed_detections(client)
    if not run_id:
        pytest.skip("No sample images")

    resp = await client.post(f"/api/inspection-runs/{run_id}/publish/arcgis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["mode"] == "mock"
    assert data["published_count"] > 0


@pytest.mark.asyncio
async def test_publish_prevents_duplicates(client):
    """Publishing twice should not re-publish already published detections."""
    run_id = await _setup_confirmed_detections(client)
    if not run_id:
        pytest.skip("No sample images")

    # First publish
    resp1 = await client.post(f"/api/inspection-runs/{run_id}/publish/arcgis")
    first_count = resp1.json()["published_count"]
    assert first_count > 0

    # Second publish — should publish zero (all already have arcgis_object_id)
    resp2 = await client.post(f"/api/inspection-runs/{run_id}/publish/arcgis")
    assert resp2.json()["published_count"] == 0


@pytest.mark.asyncio
async def test_publish_status_endpoint(client):
    """Status endpoint should show publication history."""
    run_id = await _setup_confirmed_detections(client)
    if not run_id:
        pytest.skip("No sample images")

    # Before publishing
    resp = await client.get(f"/api/inspection-runs/{run_id}/publish/arcgis/status")
    assert resp.status_code == 200
    assert resp.json()["published"] is False

    # After publishing
    await client.post(f"/api/inspection-runs/{run_id}/publish/arcgis")

    resp = await client.get(f"/api/inspection-runs/{run_id}/publish/arcgis/status")
    data = resp.json()
    assert data["published"] is True
    assert len(data["publications"]) == 1
    assert data["publications"][0]["status"] == "completed"
    assert data["publications"][0]["published_count"] > 0


@pytest.mark.asyncio
async def test_publish_updates_detection_status(client):
    """Published detections should have review_status changed to 'published'."""
    run_id = await _setup_confirmed_detections(client)
    if not run_id:
        pytest.skip("No sample images")

    await client.post(f"/api/inspection-runs/{run_id}/publish/arcgis")

    # Check detection status
    resp = await client.get(
        f"/api/inspection-runs/{run_id}/detections",
        params={"review_status": "published"},
    )
    published_dets = resp.json()
    assert len(published_dets) > 0
    for det in published_dets:
        assert det["review_status"] == "published"
        assert det["arcgis_object_id"] is not None
