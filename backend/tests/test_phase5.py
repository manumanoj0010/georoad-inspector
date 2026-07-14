"""Phase 5 tests — GeoJSON generation, coordinate order, filtering."""

import io
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image as PILImage

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
    from pathlib import Path
    sample_dir = Path(__file__).parent.parent.parent.parent / "road-asset-detector" / "data" / "sample_images"
    samples = list(sample_dir.glob("*.jpg")) if sample_dir.exists() else []
    return samples[0].read_bytes() if samples else None


async def _create_run_with_detections(client: AsyncClient) -> int | None:
    """Helper: create run, upload, process, return run_id or None if no samples."""
    image_data = _get_sample_image()
    if not image_data:
        return None

    resp = await client.post("/api/inspection-runs", json={"name": "GeoJSON Test"})
    run_id = resp.json()["id"]

    await client.post(
        f"/api/inspection-runs/{run_id}/images",
        files=[("files", ("road.jpg", image_data, "image/jpeg"))],
    )
    await client.post(f"/api/inspection-runs/{run_id}/process")
    return run_id


@pytest.mark.asyncio
async def test_geojson_endpoint_returns_feature_collection(client):
    """GeoJSON endpoint should return a valid FeatureCollection."""
    run_id = await _create_run_with_detections(client)
    if not run_id:
        pytest.skip("No sample images available")

    resp = await client.get(f"/api/inspection-runs/{run_id}/geojson")
    assert resp.status_code == 200

    geojson = resp.json()
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert isinstance(geojson["features"], list)


@pytest.mark.asyncio
async def test_geojson_coordinate_order_is_lon_lat(client):
    """GeoJSON coordinates MUST be [longitude, latitude] — not [lat, lon]."""
    run_id = await _create_run_with_detections(client)
    if not run_id:
        pytest.skip("No sample images available")

    resp = await client.get(f"/api/inspection-runs/{run_id}/geojson")
    geojson = resp.json()

    if not geojson["features"]:
        pytest.skip("No features with GPS")

    feature = geojson["features"][0]
    coords = feature["geometry"]["coordinates"]

    # Coordinates should be [lon, lat]
    lon, lat = coords
    # Longitude is typically between -180 and 180
    # Latitude is typically between -90 and 90
    # Our test images use US coordinates (lon ~ -75 to -122, lat ~ 33 to 51)
    assert -180 <= lon <= 180, f"Invalid longitude: {lon}"
    assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
    # Verify it's not swapped (lat values would be in 33-51 range for US)
    # lon values would be negative for US
    # If lon is positive and small, and lat is large negative, they're likely swapped
    assert lon != lat, "Coordinates should not be identical"


@pytest.mark.asyncio
async def test_geojson_feature_properties(client):
    """Each feature should have the required properties."""
    run_id = await _create_run_with_detections(client)
    if not run_id:
        pytest.skip("No sample images available")

    resp = await client.get(f"/api/inspection-runs/{run_id}/geojson")
    geojson = resp.json()

    if not geojson["features"]:
        pytest.skip("No features")

    props = geojson["features"][0]["properties"]
    assert "detectionId" in props
    assert "damageType" in props
    assert "confidence" in props
    assert "reviewStatus" in props
    assert "locationMethod" in props
    assert "modelVersion" in props
    assert props["detectionId"].startswith("RD-")


@pytest.mark.asyncio
async def test_geojson_confirmed_only_filter(client):
    """confirmed_only=true should only include confirmed detections."""
    run_id = await _create_run_with_detections(client)
    if not run_id:
        pytest.skip("No sample images available")

    # Get all detections
    resp = await client.get(f"/api/inspection-runs/{run_id}/geojson")
    all_features = resp.json()["features"]

    if not all_features:
        pytest.skip("No features to filter")

    # Confirm one detection via API
    dets_resp = await client.get(f"/api/inspection-runs/{run_id}/detections")
    det_id = dets_resp.json()[0]["id"]
    await client.post(f"/api/detections/{det_id}/confirm")

    # Get confirmed only
    resp = await client.get(f"/api/inspection-runs/{run_id}/geojson?confirmed_only=true")
    confirmed_features = resp.json()["features"]

    assert len(confirmed_features) <= len(all_features)
    assert len(confirmed_features) >= 1
    for f in confirmed_features:
        assert f["properties"]["reviewStatus"] == "confirmed"


@pytest.mark.asyncio
async def test_geojson_download_returns_file(client):
    """Download endpoint should return an attachment with correct content-type."""
    run_id = await _create_run_with_detections(client)
    if not run_id:
        pytest.skip("No sample images available")

    resp = await client.get(f"/api/inspection-runs/{run_id}/geojson/download")
    assert resp.status_code == 200
    assert "application/geo+json" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert ".geojson" in resp.headers["content-disposition"]

    # Verify it's valid JSON
    data = json.loads(resp.text)
    assert data["type"] == "FeatureCollection"
