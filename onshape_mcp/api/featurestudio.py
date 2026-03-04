"""Feature Studio API operations for Onshape.

Manages Feature Studio elements — create, read, and update FeatureScript code.
Used to deploy custom batch builder features that reduce API call count.
"""

from typing import Any, Dict, Optional

from .client import OnshapeClient


class FeatureStudioManager:
    """Manager for Feature Studio API operations."""

    def __init__(self, client: OnshapeClient):
        self.client = client

    async def create(
        self,
        document_id: str,
        workspace_id: str,
        name: str = "MCP Builders",
    ) -> Dict[str, Any]:
        """Create a new Feature Studio in a document.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            name: Name for the Feature Studio tab

        Returns:
            API response with element ID
        """
        path = f"/api/v9/featurestudios/d/{document_id}/w/{workspace_id}"
        data = {"name": name}
        return await self.client.post(path, data=data)

    async def get_contents(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
    ) -> Dict[str, Any]:
        """Get the FeatureScript source code from a Feature Studio.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Feature Studio element ID

        Returns:
            Response containing 'contents' field with FeatureScript source
        """
        path = f"/api/v9/featurestudios/d/{document_id}/w/{workspace_id}/e/{element_id}"
        return await self.client.get(path)

    async def update_contents(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        contents: str,
        source_microversion: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update the FeatureScript source code in a Feature Studio.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Feature Studio element ID
            contents: FeatureScript source code
            source_microversion: Optional microversion for conflict detection

        Returns:
            API response
        """
        path = f"/api/v9/featurestudios/d/{document_id}/w/{workspace_id}/e/{element_id}"
        data: Dict[str, Any] = {
            "contents": contents,
            "serializationVersion": "1.2.16",
            "rejectMicroversionSkew": False,
        }
        if source_microversion:
            data["sourceMicroversion"] = source_microversion
        return await self.client.post(path, data=data)

    async def get_specs(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
    ) -> Dict[str, Any]:
        """Get the feature specs (parameter definitions) from a Feature Studio.

        Returns the parameter schema for each custom feature defined in the
        Feature Studio. Used to understand how to invoke custom features via
        the addFeature API.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Feature Studio element ID

        Returns:
            Feature specs with parameter definitions
        """
        path = (
            f"/api/v9/featurestudios/d/{document_id}/w/{workspace_id}/e/{element_id}/featurespecs"
        )
        return await self.client.get(path)

    async def deploy_builders(
        self,
        document_id: str,
        workspace_id: str,
        name: str = "MCP Builders",
    ) -> Dict[str, str]:
        """Create a Feature Studio and populate it with MCP builder features.

        This is the main entry point for setting up batch operations in a
        document. Creates the Feature Studio and writes the builder
        FeatureScript code. Only needs to be called once per document.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            name: Name for the Feature Studio

        Returns:
            Dict with 'elementId' of the created Feature Studio
        """
        import importlib.resources

        # Create the Feature Studio
        result = await self.create(document_id, workspace_id, name)
        element_id = result.get("id", "")

        # Read the builder FeatureScript source
        fs_source = importlib.resources.files("onshape_mcp.featurescript").joinpath("builders.fs")
        contents = fs_source.read_text()

        # Upload the source code
        await self.update_contents(document_id, workspace_id, element_id, contents)

        return {"elementId": element_id}
