"""Shaded-view image capture for Onshape Part Studios and Assemblies.

Wraps the `/shadedviews` endpoints, which render the current geometry to a
PNG and return it base64-encoded. Used for visual verification of generated
geometry (e.g. an agent reading the resulting image).
"""

import base64
from pathlib import Path
from typing import Any, Dict, Optional

from .client import OnshapeClient

# Named views the Onshape API accepts directly via the `viewMatrix` query param.
NAMED_VIEWS = {"top", "bottom", "front", "back", "left", "right"}

# Onshape's API only has direct names for the six axis-aligned views; isometric
# requires an explicit 12-number view matrix (row-major 3x4, meters translation).
# Value taken from the API's own documentation example.
ISOMETRIC_VIEW_MATRIX = "0.612,0.612,0,0,-0.354,0.354,0.707,0,0.707,-0.707,0.707,0"


def _resolve_view_matrix(view: str) -> str:
    """Resolve a friendly view name to the `viewMatrix` query value.

    Args:
        view: One of the named views, "iso"/"isometric", or a raw 12-number
            comma-separated view matrix string.

    Returns:
        The value to send as the `viewMatrix` query parameter.
    """
    lowered = view.lower()
    if lowered in NAMED_VIEWS:
        return lowered
    if lowered in {"iso", "isometric"}:
        return ISOMETRIC_VIEW_MATRIX
    return view


def _extract_image_bytes(response: Dict[str, Any]) -> bytes:
    """Extract and decode the first image from a BTShadedViewsInfo response.

    Args:
        response: Raw JSON response from a `/shadedviews` endpoint.

    Returns:
        Decoded PNG image bytes.

    Raises:
        ValueError: If the response contains no image data.
    """
    images = response.get("images") or []
    for row in images:
        for encoded in row or []:
            if encoded:
                return base64.b64decode(encoded)
    raise ValueError("Onshape shaded-view response contained no image data")


class VisualsManager:
    """Manager for capturing shaded-view screenshots of Onshape geometry."""

    def __init__(self, client: OnshapeClient):
        self.client = client

    async def _capture(
        self,
        path: str,
        view: str,
        output_width: int,
        output_height: int,
        show_all_parts: bool,
        use_anti_aliasing: bool,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        params: Dict[str, Any] = {
            "viewMatrix": _resolve_view_matrix(view),
            "outputWidth": output_width,
            "outputHeight": output_height,
            "showAllParts": show_all_parts,
            "useAntiAliasing": use_anti_aliasing,
        }
        if extra_params:
            params.update(extra_params)
        response = await self.client.get(path, params=params)
        return _extract_image_bytes(response)

    async def capture_part_studio(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        view: str = "iso",
        output_width: int = 800,
        output_height: int = 600,
        show_all_parts: bool = True,
        use_anti_aliasing: bool = True,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture a shaded-view screenshot of a Part Studio.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Part Studio element ID
            view: "iso"/"isometric", a named view (top/bottom/front/back/left/right),
                or a raw 12-number view matrix string
            output_width: Image width in pixels
            output_height: Image height in pixels
            show_all_parts: Show all parts regardless of visibility settings
            use_anti_aliasing: Smooth model boundaries (slower to render)
            output_path: Optional local file path to also save the PNG to

        Returns:
            Dict with base64 `data`, `mimeType`, and (if requested) `path`
        """
        path = f"/api/v10/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/shadedviews"
        image_bytes = await self._capture(
            path, view, output_width, output_height, show_all_parts, use_anti_aliasing
        )
        return self._build_result(image_bytes, output_path)

    async def capture_assembly(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        view: str = "iso",
        output_width: int = 800,
        output_height: int = 600,
        show_all_parts: bool = True,
        use_anti_aliasing: bool = True,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture a shaded-view screenshot of an Assembly.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Assembly element ID
            view: "iso"/"isometric", a named view (top/bottom/front/back/left/right),
                or a raw 12-number view matrix string
            output_width: Image width in pixels
            output_height: Image height in pixels
            show_all_parts: Show all parts regardless of visibility settings
            use_anti_aliasing: Smooth model boundaries (slower to render)
            output_path: Optional local file path to also save the PNG to

        Returns:
            Dict with base64 `data`, `mimeType`, and (if requested) `path`
        """
        path = f"/api/v10/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/shadedviews"
        image_bytes = await self._capture(
            path, view, output_width, output_height, show_all_parts, use_anti_aliasing
        )
        return self._build_result(image_bytes, output_path)

    def _build_result(self, image_bytes: bytes, output_path: Optional[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "data": base64.b64encode(image_bytes).decode(),
            "mimeType": "image/png",
        }
        if output_path:
            path_obj = Path(output_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_bytes(image_bytes)
            result["path"] = str(path_obj)
        return result
