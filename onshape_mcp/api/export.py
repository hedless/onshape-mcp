"""Export and translation management for Onshape."""

import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional
from .client import OnshapeClient


class ExportManager:
    """Manager for exporting Onshape documents to various formats."""

    def __init__(self, client: OnshapeClient):
        self.client = client

    async def export_part_studio(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        format_name: str = "STL",
        part_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a Part Studio to a specified format.

        Uses the v11 direct translation endpoint.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Part Studio element ID
            format_name: Export format (STL, STEP, PARASOLID, GLTF, OBJ)
            part_id: Optional specific part ID to export

        Returns:
            Translation/export result with download URL or data
        """
        path = f"/api/v11/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/translations"
        data: Dict[str, Any] = {
            "formatName": format_name.upper(),
            "storeInDocument": False,
        }
        if part_id:
            data["partId"] = part_id

        return await self.client.post(path, data=data)

    async def export_assembly(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        format_name: str = "STL",
    ) -> Dict[str, Any]:
        """Export an Assembly to a specified format.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Assembly element ID
            format_name: Export format (STL, STEP, GLTF)

        Returns:
            Translation/export result
        """
        path = f"/api/v11/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/translations"
        data: Dict[str, Any] = {
            "formatName": format_name.upper(),
            "storeInDocument": False,
        }
        return await self.client.post(path, data=data)

    async def get_translation_status(
        self,
        translation_id: str,
    ) -> Dict[str, Any]:
        """Check the status of an export/translation.

        Args:
            translation_id: Translation ID from export request

        Returns:
            Translation status with state and result URL
        """
        path = f"/api/v6/translations/{translation_id}"
        return await self.client.get(path)

    async def download_external_data(self, document_id: str, external_data_id: str) -> bytes:
        """Download a translation result blob from Onshape."""
        path = f"/api/documents/d/{document_id}/externaldata/{external_data_id}"
        return await self.client.get_bytes(path)

    async def wait_for_translation(
        self,
        translation_id: str,
        timeout: float = 120.0,
        poll_interval: float = 1.0,
    ) -> Dict[str, Any]:
        """Poll translation status until it reaches a terminal state.

        Returns the final status dict. Raises TimeoutError on timeout or
        RuntimeError if the translation state is FAILED.
        """
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            status = await self.get_translation_status(translation_id)
            state = status.get("requestState")
            if state == "DONE":
                return status
            if state == "FAILED":
                raise RuntimeError(
                    f"Translation {translation_id} failed: {status.get('failureReason')}"
                )
            if asyncio.get_event_loop().time() >= deadline:
                raise TimeoutError(
                    f"Translation {translation_id} did not complete within {timeout}s (last state: {state})"
                )
            await asyncio.sleep(poll_interval)

    async def _export_to_file(
        self,
        kickoff: Callable[[], Awaitable[Dict[str, Any]]],
        output_path: str,
        timeout: float,
        poll_interval: float,
    ) -> Dict[str, Any]:
        translation = await kickoff()
        translation_id = translation.get("id")
        if not translation_id:
            raise RuntimeError(f"Export kickoff returned no translation id: {translation}")

        status = (
            translation
            if translation.get("requestState") == "DONE"
            else await self.wait_for_translation(translation_id, timeout, poll_interval)
        )

        external_ids = status.get("resultExternalDataIds") or []
        if not external_ids:
            raise RuntimeError(
                f"Translation {translation_id} finished without resultExternalDataIds"
            )
        document_id = status.get("resultDocumentId") or status.get("documentId")
        if not document_id:
            raise RuntimeError(f"Translation {translation_id} result missing documentId")

        data = await self.download_external_data(document_id, external_ids[0])
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

        return {
            "translationId": translation_id,
            "outputPath": str(path),
            "bytesWritten": len(data),
            "externalDataIds": external_ids,
        }

    async def export_part_studio_to_file(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        output_path: str,
        format_name: str = "STL",
        part_id: Optional[str] = None,
        timeout: float = 120.0,
        poll_interval: float = 1.0,
    ) -> Dict[str, Any]:
        """Export a Part Studio and write the result to disk."""
        return await self._export_to_file(
            kickoff=lambda: self.export_part_studio(
                document_id, workspace_id, element_id, format_name, part_id
            ),
            output_path=output_path,
            timeout=timeout,
            poll_interval=poll_interval,
        )

    async def export_assembly_to_file(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        output_path: str,
        format_name: str = "STL",
        timeout: float = 120.0,
        poll_interval: float = 1.0,
    ) -> Dict[str, Any]:
        """Export an Assembly and write the result to disk."""
        return await self._export_to_file(
            kickoff=lambda: self.export_assembly(
                document_id, workspace_id, element_id, format_name
            ),
            output_path=output_path,
            timeout=timeout,
            poll_interval=poll_interval,
        )
