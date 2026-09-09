"""Unit tests for VisualsManager (shaded-view screenshot capture)."""

import base64

import pytest
from unittest.mock import AsyncMock

from onshape_mcp.api.visuals import (
    VisualsManager,
    ISOMETRIC_VIEW_MATRIX,
    _resolve_view_matrix,
    _extract_image_bytes,
)

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake image data"
FAKE_PNG_B64 = base64.b64encode(FAKE_PNG_BYTES).decode()


def _shaded_view_response(encoded: str = FAKE_PNG_B64):
    return {"images": [[encoded]]}


class TestResolveViewMatrix:
    """Test friendly view-name resolution."""

    @pytest.mark.parametrize("view", ["top", "bottom", "front", "back", "left", "right"])
    def test_named_views_pass_through_lowercased(self, view):
        assert _resolve_view_matrix(view.upper()) == view

    def test_iso_resolves_to_isometric_matrix(self):
        assert _resolve_view_matrix("iso") == ISOMETRIC_VIEW_MATRIX
        assert _resolve_view_matrix("isometric") == ISOMETRIC_VIEW_MATRIX

    def test_raw_matrix_passed_through_unchanged(self):
        raw = "1,0,0,0,0,1,0,0,0,0,1,0"
        assert _resolve_view_matrix(raw) == raw


class TestExtractImageBytes:
    """Test decoding the BTShadedViewsInfo response shape."""

    def test_extracts_first_image(self):
        response = _shaded_view_response()
        assert _extract_image_bytes(response) == FAKE_PNG_BYTES

    def test_raises_on_empty_images(self):
        with pytest.raises(ValueError):
            _extract_image_bytes({"images": []})

    def test_raises_on_missing_images_key(self):
        with pytest.raises(ValueError):
            _extract_image_bytes({})


class TestVisualsManager:
    """Test VisualsManager operations."""

    @pytest.fixture
    def visuals_manager(self, onshape_client):
        return VisualsManager(onshape_client)

    @pytest.mark.asyncio
    async def test_capture_part_studio_default_iso_view(
        self, visuals_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value=_shaded_view_response())

        result = await visuals_manager.capture_part_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert result["mimeType"] == "image/png"
        assert base64.b64decode(result["data"]) == FAKE_PNG_BYTES
        assert "path" not in result

        onshape_client.get.assert_called_once()
        call_args = onshape_client.get.call_args
        path = call_args[0][0]
        assert "partstudios" in path
        assert sample_document_ids["document_id"] in path
        assert sample_document_ids["workspace_id"] in path
        assert sample_document_ids["element_id"] in path
        assert "shadedviews" in path

        params = call_args[1]["params"]
        assert params["viewMatrix"] == ISOMETRIC_VIEW_MATRIX
        assert params["outputWidth"] == 800
        assert params["outputHeight"] == 600

    @pytest.mark.asyncio
    async def test_capture_part_studio_named_view(
        self, visuals_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value=_shaded_view_response())

        await visuals_manager.capture_part_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            view="top",
            output_width=400,
            output_height=300,
        )

        params = onshape_client.get.call_args[1]["params"]
        assert params["viewMatrix"] == "top"
        assert params["outputWidth"] == 400
        assert params["outputHeight"] == 300

    @pytest.mark.asyncio
    async def test_capture_part_studio_saves_to_output_path(
        self, visuals_manager, onshape_client, sample_document_ids, tmp_path
    ):
        onshape_client.get = AsyncMock(return_value=_shaded_view_response())
        output_path = tmp_path / "nested" / "screenshot.png"

        result = await visuals_manager.capture_part_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            output_path=str(output_path),
        )

        assert result["path"] == str(output_path)
        assert output_path.read_bytes() == FAKE_PNG_BYTES

    @pytest.mark.asyncio
    async def test_capture_assembly_uses_assemblies_path(
        self, visuals_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value=_shaded_view_response())

        result = await visuals_manager.capture_assembly(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert base64.b64decode(result["data"]) == FAKE_PNG_BYTES
        path = onshape_client.get.call_args[0][0]
        assert "assemblies" in path
        assert "shadedviews" in path

    @pytest.mark.asyncio
    async def test_capture_raises_when_no_image_returned(
        self, visuals_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value={"images": []})

        with pytest.raises(ValueError):
            await visuals_manager.capture_part_studio(
                sample_document_ids["document_id"],
                sample_document_ids["workspace_id"],
                sample_document_ids["element_id"],
            )
