"""Tests for Feature Studio API operations."""

import pytest
from unittest.mock import AsyncMock

from onshape_mcp.api.featurestudio import FeatureStudioManager


@pytest.fixture
def mock_client():
    client = AsyncMock()
    return client


@pytest.fixture
def manager(mock_client):
    return FeatureStudioManager(mock_client)


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_feature_studio(self, manager, mock_client):
        mock_client.post.return_value = {"id": "abc123", "name": "MCP Builders"}

        result = await manager.create("doc1", "ws1", "MCP Builders")

        mock_client.post.assert_called_once_with(
            "/api/v9/featurestudios/d/doc1/w/ws1",
            data={"name": "MCP Builders"},
        )
        assert result["id"] == "abc123"

    @pytest.mark.asyncio
    async def test_create_default_name(self, manager, mock_client):
        mock_client.post.return_value = {"id": "abc123"}

        await manager.create("doc1", "ws1")

        call_data = mock_client.post.call_args[1]["data"]
        assert call_data["name"] == "MCP Builders"


class TestGetContents:
    @pytest.mark.asyncio
    async def test_get_contents(self, manager, mock_client):
        mock_client.get.return_value = {"contents": "FeatureScript 2892;"}

        result = await manager.get_contents("doc1", "ws1", "elem1")

        mock_client.get.assert_called_once_with("/api/v9/featurestudios/d/doc1/w/ws1/e/elem1")
        assert result["contents"] == "FeatureScript 2892;"


class TestUpdateContents:
    @pytest.mark.asyncio
    async def test_update_contents(self, manager, mock_client):
        mock_client.post.return_value = {"contents": "updated"}

        await manager.update_contents("doc1", "ws1", "elem1", "FeatureScript 2892;\n// code")

        call_data = mock_client.post.call_args[1]["data"]
        assert call_data["contents"] == "FeatureScript 2892;\n// code"
        assert call_data["serializationVersion"] == "1.2.16"
        assert call_data["rejectMicroversionSkew"] is False

    @pytest.mark.asyncio
    async def test_update_with_microversion(self, manager, mock_client):
        mock_client.post.return_value = {}

        await manager.update_contents("doc1", "ws1", "elem1", "code", source_microversion="mv123")

        call_data = mock_client.post.call_args[1]["data"]
        assert call_data["sourceMicroversion"] == "mv123"

    @pytest.mark.asyncio
    async def test_update_without_microversion(self, manager, mock_client):
        mock_client.post.return_value = {}

        await manager.update_contents("doc1", "ws1", "elem1", "code")

        call_data = mock_client.post.call_args[1]["data"]
        assert "sourceMicroversion" not in call_data


class TestGetSpecs:
    @pytest.mark.asyncio
    async def test_get_specs(self, manager, mock_client):
        mock_client.get.return_value = {"featureSpecs": []}

        result = await manager.get_specs("doc1", "ws1", "elem1")

        mock_client.get.assert_called_once_with(
            "/api/v9/featurestudios/d/doc1/w/ws1/e/elem1/featurespecs"
        )
        assert result["featureSpecs"] == []


class TestDeployBuilders:
    @pytest.mark.asyncio
    async def test_deploy_creates_and_uploads(self, manager, mock_client):
        mock_client.post.return_value = {"id": "fs_elem_123"}

        result = await manager.deploy_builders("doc1", "ws1")

        assert result["elementId"] == "fs_elem_123"
        # Should have 2 POST calls: create + update contents
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_deploy_uploads_featurescript(self, manager, mock_client):
        mock_client.post.return_value = {"id": "fs_elem_123"}

        await manager.deploy_builders("doc1", "ws1")

        # Second call is the update contents
        update_call = mock_client.post.call_args_list[1]
        contents = update_call[1]["data"]["contents"]
        assert "FeatureScript 2892" in contents
        assert "rectExtrude" in contents
        assert "cabinetBox" in contents

    @pytest.mark.asyncio
    async def test_deploy_custom_name(self, manager, mock_client):
        mock_client.post.return_value = {"id": "fs_elem_123"}

        await manager.deploy_builders("doc1", "ws1", name="Custom Builders")

        create_call = mock_client.post.call_args_list[0]
        assert create_call[1]["data"]["name"] == "Custom Builders"
