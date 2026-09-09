"""Unit tests for Variable manager."""

import pytest
from unittest.mock import AsyncMock

from onshape_mcp.api.variables import VariableManager, Variable, _infer_variable_type


class TestVariable:
    """Test Variable model."""

    def test_variable_creation_with_description(self):
        """Test creating a variable with description."""
        var = Variable(name="width", expression="10 in", description="Part width")

        assert var.name == "width"
        assert var.expression == "10 in"
        assert var.description == "Part width"

    def test_variable_creation_without_description(self):
        """Test creating a variable without description."""
        var = Variable(name="height", expression="5 in")

        assert var.name == "height"
        assert var.expression == "5 in"
        assert var.description is None

    def test_variable_creation_with_type(self):
        """Test creating a variable with type."""
        var = Variable(name="width", expression="10 in", type="LENGTH")

        assert var.type == "LENGTH"

    def test_variable_requires_name(self):
        """Test that name is required."""
        with pytest.raises(Exception):
            Variable(expression="10 in")

    def test_variable_requires_expression(self):
        """Test that expression is required."""
        with pytest.raises(Exception):
            Variable(name="width")


class TestInferVariableType:
    """Test _infer_variable_type helper."""

    def test_length_inches(self):
        assert _infer_variable_type("0.75 in") == "LENGTH"

    def test_length_mm(self):
        assert _infer_variable_type("19 mm") == "LENGTH"

    def test_angle_degrees(self):
        assert _infer_variable_type("45 deg") == "ANGLE"

    def test_angle_radians(self):
        assert _infer_variable_type("3.14 rad") == "ANGLE"

    def test_plain_number(self):
        assert _infer_variable_type("42") == "ANY"

    def test_unknown_unit(self):
        assert _infer_variable_type("5 foo") == "ANY"

    def test_whitespace_handling(self):
        assert _infer_variable_type("  10 in  ") == "LENGTH"


class TestVariableManager:
    """Test VariableManager operations."""

    @pytest.fixture
    def variable_manager(self, onshape_client):
        """Provide a VariableManager instance."""
        return VariableManager(onshape_client)

    @pytest.mark.asyncio
    async def test_create_variable_studio(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """Test creating a Variable Studio."""
        onshape_client.post = AsyncMock(return_value={"id": "vs_element_123", "name": "Variables"})

        result = await variable_manager.create_variable_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            "Variables",
        )

        assert result["id"] == "vs_element_123"
        assert result["name"] == "Variables"

        # Verify correct path
        call_args = onshape_client.post.call_args
        path = call_args[0][0]
        assert "/api/variables/d/" in path
        assert path.endswith("/variablestudio")

        # Verify payload
        data = call_args[1]["data"]
        assert data["name"] == "Variables"

    @pytest.mark.asyncio
    async def test_get_variables_success(
        self, variable_manager, onshape_client, sample_document_ids, sample_variables
    ):
        """Test getting variables from a Variable Studio."""
        onshape_client.get = AsyncMock(return_value=sample_variables)

        result = await variable_manager.get_variables(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert len(result) == 2
        assert all(isinstance(v, Variable) for v in result)

        # Check first variable
        assert result[0].name == "width"
        assert result[0].expression == "10 in"
        assert result[0].description == "Width of the part"
        assert result[0].type == "LENGTH"

        # Check second variable (no description)
        assert result[1].name == "height"
        assert result[1].expression == "5 in"
        assert result[1].description is None

        # Verify correct path
        call_args = onshape_client.get.call_args
        path = call_args[0][0]
        assert "/variables" in path

    @pytest.mark.asyncio
    async def test_get_variables_empty_list(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """Test getting variables when none exist."""
        onshape_client.get = AsyncMock(return_value=[{"variableStudioReference": None, "variables": []}])

        result = await variable_manager.get_variables(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_variables_empty_response(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """Test getting variables when response is completely empty."""
        onshape_client.get = AsyncMock(return_value=[])

        result = await variable_manager.get_variables(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_variables_handles_missing_fields(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """Test handling variables with missing optional fields."""
        variables_data = [
            {
                "variableStudioReference": None,
                "variables": [
                    {"name": "var1", "expression": "1 in"},
                    {"expression": "2 in"},  # Missing name
                    {"name": "var2"},  # Missing expression
                ],
            }
        ]

        onshape_client.get = AsyncMock(return_value=variables_data)

        result = await variable_manager.get_variables(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        # Should handle missing fields gracefully with empty strings
        assert result[0].name == "var1"
        assert result[1].name == ""
        assert result[2].expression == ""

    @pytest.mark.asyncio
    async def test_get_variables_uses_correct_endpoint(
        self, variable_manager, onshape_client, sample_document_ids, sample_variables
    ):
        """Test that get_variables uses the variables endpoint without version."""
        onshape_client.get = AsyncMock(return_value=sample_variables)

        await variable_manager.get_variables(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        call_args = onshape_client.get.call_args
        path = call_args[0][0]
        assert "/api/variables/d/" in path
        assert "/variables" in path
        assert "/partstudios/" not in path

    @pytest.fixture
    def empty_variable_studio(self):
        """Return an empty Variable Studio GET response."""
        return [{"variableStudioReference": None, "variables": []}]

    @pytest.fixture
    def existing_variables_response(self):
        """Return a GET response with existing variables."""
        return [
            {
                "variableStudioReference": None,
                "variables": [
                    {"name": "width", "expression": "10 in", "type": "LENGTH", "description": "Width of the part"},
                    {"name": "height", "expression": "5 in", "type": "LENGTH"},
                ],
            }
        ]

    @pytest.mark.asyncio
    async def test_set_variable_uses_correct_endpoint(
        self, variable_manager, onshape_client, sample_document_ids, empty_variable_studio
    ):
        """Test that set_variable uses the variables endpoint without version."""
        onshape_client.get = AsyncMock(return_value=empty_variable_studio)
        onshape_client.post = AsyncMock(return_value={})

        await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "test_var",
            "1 in",
        )

        call_args = onshape_client.post.call_args
        path = call_args[0][0]
        assert "/api/variables/d/" in path
        assert "/variables" in path
        assert "/partstudios/" not in path

    @pytest.mark.asyncio
    async def test_set_variable_with_description(
        self, variable_manager, onshape_client, sample_document_ids, empty_variable_studio
    ):
        """Test setting a variable with description."""
        onshape_client.get = AsyncMock(return_value=empty_variable_studio)
        onshape_client.post = AsyncMock(return_value={})

        result = await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "thickness",
            "0.25 in",
            "Material thickness",
        )

        assert result == {}

        # Verify data payload
        call_args = onshape_client.post.call_args
        data = call_args[1]["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "thickness"
        assert data[0]["expression"] == "0.25 in"
        assert data[0]["type"] == "LENGTH"
        assert data[0]["description"] == "Material thickness"

    @pytest.mark.asyncio
    async def test_set_variable_without_description(
        self, variable_manager, onshape_client, sample_document_ids, empty_variable_studio
    ):
        """Test setting a variable without description."""
        onshape_client.get = AsyncMock(return_value=empty_variable_studio)
        onshape_client.post = AsyncMock(return_value={})

        await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "depth",
            "1.5 in",
        )

        # Verify payload includes type but not description
        call_args = onshape_client.post.call_args
        data = call_args[1]["data"]
        assert isinstance(data, list)
        assert data[0]["name"] == "depth"
        assert data[0]["expression"] == "1.5 in"
        assert data[0]["type"] == "LENGTH"
        assert "description" not in data[0]

    @pytest.mark.asyncio
    async def test_set_variable_infers_angle_type(
        self, variable_manager, onshape_client, sample_document_ids, empty_variable_studio
    ):
        """Test that set_variable infers ANGLE type from deg expression."""
        onshape_client.get = AsyncMock(return_value=empty_variable_studio)
        onshape_client.post = AsyncMock(return_value={})

        await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "draft",
            "5 deg",
        )

        call_args = onshape_client.post.call_args
        data = call_args[1]["data"]
        assert data[0]["type"] == "ANGLE"

    @pytest.mark.asyncio
    async def test_set_variable_infers_any_type(
        self, variable_manager, onshape_client, sample_document_ids, empty_variable_studio
    ):
        """Test that set_variable infers ANY type for plain numbers."""
        onshape_client.get = AsyncMock(return_value=empty_variable_studio)
        onshape_client.post = AsyncMock(return_value={})

        await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "count",
            "4",
        )

        call_args = onshape_client.post.call_args
        data = call_args[1]["data"]
        assert data[0]["type"] == "ANY"

    @pytest.mark.asyncio
    async def test_set_variable_preserves_existing(
        self, variable_manager, onshape_client, sample_document_ids, existing_variables_response
    ):
        """Test that setting a new variable preserves existing ones."""
        onshape_client.get = AsyncMock(return_value=existing_variables_response)
        onshape_client.post = AsyncMock(return_value={})

        await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "depth",
            "2 in",
        )

        call_args = onshape_client.post.call_args
        data = call_args[1]["data"]
        assert len(data) == 3
        names = [v["name"] for v in data]
        assert "width" in names
        assert "height" in names
        assert "depth" in names

    @pytest.mark.asyncio
    async def test_set_variable_updates_existing(
        self, variable_manager, onshape_client, sample_document_ids, existing_variables_response
    ):
        """Test updating an existing variable replaces it in-place."""
        onshape_client.get = AsyncMock(return_value=existing_variables_response)
        onshape_client.post = AsyncMock(return_value={})

        await variable_manager.set_variable(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "width",
            "15 in",
            "Updated width",
        )

        call_args = onshape_client.post.call_args
        data = call_args[1]["data"]
        # Should still be 2 variables, not 3
        assert len(data) == 2
        # width should be updated
        width_var = next(v for v in data if v["name"] == "width")
        assert width_var["expression"] == "15 in"
        assert width_var["description"] == "Updated width"
        # height should be preserved
        height_var = next(v for v in data if v["name"] == "height")
        assert height_var["expression"] == "5 in"

    @pytest.mark.asyncio
    async def test_get_configuration_definition_success(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """Test getting configuration definition."""
        expected_config = {
            "configurationParameters": [
                {"parameterId": "param1", "type": "BTMConfigurationParameterEnum"}
            ]
        }

        onshape_client.get = AsyncMock(return_value=expected_config)

        result = await variable_manager.get_configuration_definition(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert result == expected_config

        # Verify path includes /configuration
        call_args = onshape_client.get.call_args
        path = call_args[0][0]
        assert "/configuration" in path

    @pytest.mark.asyncio
    async def test_variable_manager_api_error_handling(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """Test that API errors are propagated correctly."""
        onshape_client.get = AsyncMock(side_effect=Exception("Network error"))

        with pytest.raises(Exception) as exc_info:
            await variable_manager.get_variables(
                sample_document_ids["document_id"],
                sample_document_ids["workspace_id"],
                sample_document_ids["element_id"],
            )

        assert "Network error" in str(exc_info.value)
