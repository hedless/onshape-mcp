"""Unit tests for Metadata manager."""

import pytest
from unittest.mock import AsyncMock

from onshape_mcp.api.metadata import MetadataManager


def _enum_param(param_id, name, options):
    """Build a wrapped enum configuration parameter as Onshape returns it."""
    return {
        "typeName": "BTMConfigurationParameterEnum",
        "message": {
            "parameterId": param_id,
            "parameterName": name,
            "options": [
                {"message": {"option": value, "optionName": label}} for value, label in options
            ],
        },
    }


class TestMetadataManager:
    """Test MetadataManager operations."""

    @pytest.fixture
    def metadata_manager(self, onshape_client):
        """Provide a MetadataManager instance."""
        return MetadataManager(onshape_client)

    @pytest.mark.asyncio
    async def test_get_element_metadata(self, metadata_manager, onshape_client):
        onshape_client.get = AsyncMock(return_value={"properties": []})

        await metadata_manager.get_element_metadata("d1", "w", "w1", "e1")

        path = onshape_client.get.call_args[0][0]
        params = onshape_client.get.call_args[1]["params"]
        assert path == "/api/v6/metadata/d/d1/w/w1/e/e1"
        assert params == {"depth": 1, "includePropertyDefaults": "true"}

    @pytest.mark.asyncio
    async def test_get_element_metadata_with_configuration(self, metadata_manager, onshape_client):
        onshape_client.get = AsyncMock(return_value={})

        await metadata_manager.get_element_metadata("d1", "v", "v1", "e1", configuration="a=b")

        assert onshape_client.get.call_args[0][0] == "/api/v6/metadata/d/d1/v/v1/e/e1"
        assert onshape_client.get.call_args[1]["params"]["configuration"] == "a=b"

    @pytest.mark.asyncio
    async def test_get_part_metadata(self, metadata_manager, onshape_client):
        onshape_client.get = AsyncMock(return_value={})

        await metadata_manager.get_part_metadata("d1", "w", "w1", "e1", "JHD")

        assert onshape_client.get.call_args[0][0] == "/api/v6/metadata/d/d1/w/w1/e/e1/p/JHD"
        assert "configuration" not in onshape_client.get.call_args[1]["params"]

    @pytest.mark.asyncio
    async def test_get_assembly_bom(self, metadata_manager, onshape_client):
        onshape_client.get = AsyncMock(return_value={"headers": [], "rows": []})

        await metadata_manager.get_assembly_bom("d1", "v", "v1", "e1", indented=False)

        path = onshape_client.get.call_args[0][0]
        params = onshape_client.get.call_args[1]["params"]
        assert path == "/api/v6/assemblies/d/d1/v/v1/e/e1/bom"
        assert params["indented"] == "false"
        assert params["multiLevel"] == "true"
        assert params["generateIfAbsent"] == "true"

    @pytest.mark.asyncio
    async def test_get_configuration(self, metadata_manager, onshape_client):
        onshape_client.get = AsyncMock(return_value={"configurationParameters": []})

        await metadata_manager.get_configuration("d1", "w", "w1", "e1")

        onshape_client.get.assert_called_once_with("/api/v6/elements/d/d1/w/w1/e/e1/configuration")


class TestFlattenBomRows:
    """Test BOM row flattening."""

    def test_rows_keyed_by_header_name(self):
        bom = {
            "headers": [{"id": "h1", "name": "Part number"}, {"id": "h2", "name": "Quantity"}],
            "rows": [{"headerIdToValue": {"h1": "PN-001", "h2": 2}}],
        }
        assert MetadataManager.flatten_bom_rows(bom) == [{"Part number": "PN-001", "Quantity": 2}]

    def test_display_name_values_unwrapped(self):
        bom = {
            "headers": [{"id": "h1", "name": "Material"}],
            "rows": [{"headerIdToValue": {"h1": {"displayName": "Aluminum 6061", "id": "x"}}}],
        }
        assert MetadataManager.flatten_bom_rows(bom) == [{"Material": "Aluminum 6061"}]

    def test_unknown_header_keeps_id(self):
        bom = {"headers": [], "rows": [{"headerIdToValue": {"h9": "v"}}]}
        assert MetadataManager.flatten_bom_rows(bom) == [{"h9": "v"}]

    def test_empty_bom(self):
        assert MetadataManager.flatten_bom_rows({}) == []


class TestParseConfigParams:
    """Test configuration definition parsing."""

    def test_wrapped_enum(self):
        definition = {
            "configurationParameters": [
                _enum_param("finish", "Finish", [("BLK", "Black"), ("WHT", "White")])
            ]
        }
        assert MetadataManager.parse_config_params(definition) == [
            {
                "id": "finish",
                "name": "Finish",
                "type": "enum",
                "options": [{"value": "BLK", "name": "Black"}, {"value": "WHT", "name": "White"}],
            }
        ]

    def test_flat_shapes_and_types(self):
        definition = {
            "configurationParameters": [
                {"btType": "BTMConfigurationParameterBoolean", "parameterId": "b"},
                {"typeName": "BTMConfigurationParameterQuantity", "parameterId": "q"},
                {"typeName": "BTMConfigurationParameterString", "parameterId": "s"},
            ]
        }
        parsed = MetadataManager.parse_config_params(definition)
        assert [(p["id"], p["name"], p["type"]) for p in parsed] == [
            ("b", "b", "boolean"),
            ("q", "q", "quantity"),
            ("s", "s", "string"),
        ]

    def test_no_parameters(self):
        assert MetadataManager.parse_config_params({}) == []


class TestGetConfiguredProperties:
    """Test variant expansion."""

    @pytest.fixture
    def metadata_manager(self, onshape_client):
        return MetadataManager(onshape_client)

    @pytest.mark.asyncio
    async def test_expands_every_combination(self, metadata_manager, onshape_client):
        definition = {
            "configurationParameters": [
                _enum_param("finish", "Finish", [("BLK", "Black"), ("WHT", "White")]),
                _enum_param("len", "Length", [("L2", "2 ft"), ("L4", "4 ft")]),
            ]
        }

        async def fake_get(path, params=None):
            if path.endswith("/configuration"):
                return definition
            return {"properties": [{"name": "Part number", "value": params["configuration"]}]}

        onshape_client.get = AsyncMock(side_effect=fake_get)

        result = await metadata_manager.get_configured_properties("d1", "w", "w1", "e1")

        assert result["variant_count"] == 4
        assert onshape_client.get.call_count == 5
        first = result["variants"][0]
        assert first["configuration"] == {"Finish": "Black", "Length": "2 ft"}
        assert first["properties"] == {"Part number": "finish=BLK;len=L2"}

    @pytest.mark.asyncio
    async def test_no_enum_inputs_reads_once(self, metadata_manager, onshape_client):
        async def fake_get(path, params=None):
            if path.endswith("/configuration"):
                return {"configurationParameters": []}
            assert "configuration" not in params
            return {"properties": [{"name": "Name", "value": "Bracket"}]}

        onshape_client.get = AsyncMock(side_effect=fake_get)

        result = await metadata_manager.get_configured_properties("d1", "w", "w1", "e1")

        assert result["variant_count"] == 1
        assert result["variants"][0] == {"configuration": {}, "properties": {"Name": "Bracket"}}

    @pytest.mark.asyncio
    async def test_cap_stops_before_metadata_calls(self, metadata_manager, onshape_client):
        definition = {
            "configurationParameters": [
                _enum_param("a", "A", [(str(i), str(i)) for i in range(5)]),
                _enum_param("b", "B", [(str(i), str(i)) for i in range(5)]),
            ]
        }
        onshape_client.get = AsyncMock(return_value=definition)

        result = await metadata_manager.get_configured_properties(
            "d1", "w", "w1", "e1", max_variants=10
        )

        assert result["variant_count"] == 25
        assert "_warning" in result
        assert onshape_client.get.call_count == 1
