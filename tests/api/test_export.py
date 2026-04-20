"""Unit tests for Export manager."""

import pytest
from unittest.mock import AsyncMock

from onshape_mcp.api.export import ExportManager


class TestExportManager:
    """Test ExportManager operations."""

    @pytest.fixture
    def export_manager(self, onshape_client):
        """Provide an ExportManager instance."""
        return ExportManager(onshape_client)

    @pytest.mark.asyncio
    async def test_export_part_studio_stl(
        self, export_manager, onshape_client, sample_document_ids
    ):
        """Test exporting a Part Studio to STL format."""
        expected_response = {
            "id": "translation_123",
            "requestState": "ACTIVE",
        }

        onshape_client.post = AsyncMock(return_value=expected_response)

        result = await export_manager.export_part_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            format_name="STL",
        )

        assert result == expected_response
        onshape_client.post.assert_called_once()

        call_args = onshape_client.post.call_args
        body = call_args[1]["data"]
        assert body["formatName"] == "STL"

        path = call_args[0][0]
        assert sample_document_ids["document_id"] in path
        assert sample_document_ids["workspace_id"] in path
        assert sample_document_ids["element_id"] in path

    @pytest.mark.asyncio
    async def test_export_part_studio_with_part_id(
        self, export_manager, onshape_client, sample_document_ids
    ):
        """Test exporting a specific part by part ID."""
        part_id = "JHD"
        expected_response = {"id": "translation_456", "requestState": "ACTIVE"}

        onshape_client.post = AsyncMock(return_value=expected_response)

        result = await export_manager.export_part_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            format_name="STEP",
            part_id=part_id,
        )

        assert result == expected_response
        onshape_client.post.assert_called_once()

        call_args = onshape_client.post.call_args
        body = call_args[1]["data"]
        assert body["partId"] == part_id
        assert body["formatName"] == "STEP"

    @pytest.mark.asyncio
    async def test_export_assembly_success(
        self, export_manager, onshape_client, sample_document_ids
    ):
        """Test exporting an assembly POSTs to the assemblies path."""
        expected_response = {"id": "translation_789", "requestState": "ACTIVE"}

        onshape_client.post = AsyncMock(return_value=expected_response)

        result = await export_manager.export_assembly(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            format_name="STL",
        )

        assert result == expected_response
        onshape_client.post.assert_called_once()

        call_args = onshape_client.post.call_args
        path = call_args[0][0]
        assert "assemblies" in path
        assert sample_document_ids["document_id"] in path
        assert sample_document_ids["workspace_id"] in path
        assert sample_document_ids["element_id"] in path

        body = call_args[1]["data"]
        assert body["formatName"] == "STL"

    @pytest.mark.asyncio
    async def test_get_translation_status(self, export_manager, onshape_client):
        """Test checking the status of a translation by ID."""
        translation_id = "trans_id_abc123"
        expected_response = {
            "id": translation_id,
            "requestState": "DONE",
            "resultExternalDataIds": ["file_data_id_xyz"],
        }

        onshape_client.get = AsyncMock(return_value=expected_response)

        result = await export_manager.get_translation_status(translation_id)

        assert result == expected_response
        onshape_client.get.assert_called_once()

        call_args = onshape_client.get.call_args
        path = call_args[0][0]
        assert translation_id in path

    @pytest.mark.asyncio
    async def test_download_external_data(self, export_manager, onshape_client):
        """Test downloading a translation result blob returns the raw bytes."""
        onshape_client.get_bytes = AsyncMock(return_value=b"PARASOLID_PAYLOAD")

        result = await export_manager.download_external_data("doc1", "ext1")

        assert result == b"PARASOLID_PAYLOAD"
        path = onshape_client.get_bytes.call_args[0][0]
        assert "doc1" in path
        assert "ext1" in path
        assert "externaldata" in path

    @pytest.mark.asyncio
    async def test_wait_for_translation_returns_on_done(self, export_manager, onshape_client):
        """wait_for_translation polls until state is DONE."""
        onshape_client.get = AsyncMock(
            side_effect=[
                {"requestState": "ACTIVE"},
                {"requestState": "DONE", "resultExternalDataIds": ["x"]},
            ]
        )

        result = await export_manager.wait_for_translation("t1", poll_interval=0.0)

        assert result["requestState"] == "DONE"
        assert onshape_client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_translation_raises_on_failure(self, export_manager, onshape_client):
        """wait_for_translation raises RuntimeError when translation fails."""
        onshape_client.get = AsyncMock(
            return_value={"requestState": "FAILED", "failureReason": "boom"}
        )

        with pytest.raises(RuntimeError, match="boom"):
            await export_manager.wait_for_translation("t1", poll_interval=0.0)

    @pytest.mark.asyncio
    async def test_export_part_studio_to_file_writes_bytes(
        self, export_manager, onshape_client, sample_document_ids, tmp_path
    ):
        """export_part_studio_to_file kicks off, polls, downloads, and writes to disk."""
        onshape_client.post = AsyncMock(return_value={"id": "t99", "requestState": "ACTIVE"})
        onshape_client.get = AsyncMock(
            return_value={
                "id": "t99",
                "requestState": "DONE",
                "resultExternalDataIds": ["ext99"],
                "resultDocumentId": sample_document_ids["document_id"],
            }
        )
        onshape_client.get_bytes = AsyncMock(return_value=b"PARASOLID_BYTES")

        out = tmp_path / "nested" / "cube.x_t"
        result = await export_manager.export_part_studio_to_file(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            output_path=str(out),
            format_name="PARASOLID",
            poll_interval=0.0,
        )

        assert out.read_bytes() == b"PARASOLID_BYTES"
        assert result["translationId"] == "t99"
        assert result["bytesWritten"] == len(b"PARASOLID_BYTES")
        assert result["outputPath"] == str(out)

    @pytest.mark.asyncio
    async def test_export_part_studio_to_file_skips_poll_when_done(
        self, export_manager, onshape_client, sample_document_ids, tmp_path
    ):
        """If the kickoff already returns DONE, we skip polling entirely."""
        onshape_client.post = AsyncMock(
            return_value={
                "id": "t100",
                "requestState": "DONE",
                "resultExternalDataIds": ["ext100"],
                "resultDocumentId": sample_document_ids["document_id"],
            }
        )
        onshape_client.get = AsyncMock()
        onshape_client.get_bytes = AsyncMock(return_value=b"DATA")

        out = tmp_path / "out.stl"
        await export_manager.export_part_studio_to_file(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            output_path=str(out),
            poll_interval=0.0,
        )

        onshape_client.get.assert_not_called()
        assert out.read_bytes() == b"DATA"

    @pytest.mark.asyncio
    async def test_export_assembly_to_file_uses_assembly_path(
        self, export_manager, onshape_client, sample_document_ids, tmp_path
    ):
        """export_assembly_to_file hits the assemblies translations path."""
        onshape_client.post = AsyncMock(
            return_value={
                "id": "t200",
                "requestState": "DONE",
                "resultExternalDataIds": ["ext200"],
                "resultDocumentId": sample_document_ids["document_id"],
            }
        )
        onshape_client.get_bytes = AsyncMock(return_value=b"STL_DATA")

        out = tmp_path / "asm.stl"
        await export_manager.export_assembly_to_file(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            output_path=str(out),
            poll_interval=0.0,
        )

        assert out.read_bytes() == b"STL_DATA"
        path = onshape_client.post.call_args[0][0]
        assert "assemblies" in path
