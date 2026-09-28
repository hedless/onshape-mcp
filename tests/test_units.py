"""Tests for the configurable length unit (ONSHAPE_LENGTH_UNIT)."""

import pytest

from onshape_mcp.analysis.interference import (
    InterferenceResult,
    OverlapInfo,
    format_interference_result,
)
from onshape_mcp.analysis.positioning import (
    InstancePositionInfo,
    build_absolute_translation_matrix,
    format_positions_report,
)
from onshape_mcp.builders.extrude import ExtrudeBuilder
from onshape_mcp.builders.mate import build_transform_matrix
from onshape_mcp.builders.sketch import SketchBuilder
from onshape_mcp.builders.thicken import ThickenBuilder
from onshape_mcp.server import list_tools
from onshape_mcp.units import (
    format_length,
    from_meters,
    length_expression,
    length_unit,
    to_meters,
)


@pytest.fixture
def centimeters(monkeypatch):
    monkeypatch.setenv("ONSHAPE_LENGTH_UNIT", "cm")


class TestLengthUnit:
    def test_defaults_to_inches(self):
        assert length_unit().expression == "in"
        assert to_meters(1) == pytest.approx(0.0254)
        assert length_expression(2) == "2 in"
        assert format_length(1.5) == '1.500"'

    def test_empty_value_means_inches(self, monkeypatch):
        monkeypatch.setenv("ONSHAPE_LENGTH_UNIT", "")
        assert length_unit().expression == "in"

    @pytest.mark.parametrize(
        "value, meters", [("in", 0.0254), ("mm", 0.001), ("cm", 0.01), ("m", 1.0)]
    )
    def test_supported_units(self, monkeypatch, value, meters):
        monkeypatch.setenv("ONSHAPE_LENGTH_UNIT", value)
        assert to_meters(1) == pytest.approx(meters)
        assert from_meters(meters) == pytest.approx(1)

    def test_ignores_case_and_whitespace(self, monkeypatch):
        monkeypatch.setenv("ONSHAPE_LENGTH_UNIT", " CM ")
        assert length_unit().name == "centimeters"

    def test_rejects_unknown_unit(self, monkeypatch):
        monkeypatch.setenv("ONSHAPE_LENGTH_UNIT", "ft")
        with pytest.raises(ValueError, match="in, mm, cm, m"):
            length_unit()

    def test_centimeter_helpers(self, centimeters):
        assert to_meters(2.5) == pytest.approx(0.025)
        assert from_meters(0.55) == pytest.approx(55)
        assert length_expression(2.5) == "2.5 cm"
        assert format_length(55) == "55.000 cm"


class TestBuildersInCentimeters:
    def test_extrude_depth_expression(self, centimeters):
        extrude = ExtrudeBuilder(sketch_feature_id="sk1", depth=1.8)
        params = extrude.build()["feature"]["parameters"]
        depth = next(p for p in params if p["parameterId"] == "depth")
        assert depth["expression"] == "1.8 cm"

    def test_thicken_expressions(self, centimeters):
        thicken = ThickenBuilder("Thicken", sketch_feature_id="sk1").set_thickness(0.4)
        params = thicken.build()["feature"]["parameters"]
        expressions = {p["parameterId"]: p.get("expression") for p in params}
        assert expressions["thickness1"] == "0.4 cm"
        assert expressions["thickness2"] == "0 cm"

    def test_sketch_coordinates_converted_to_meters(self, centimeters):
        sketch = SketchBuilder().add_circle(center=(10, 20), radius=5)
        geometry = sketch.entities[0]["geometry"]
        assert geometry["xCenter"] == pytest.approx(0.10)
        assert geometry["yCenter"] == pytest.approx(0.20)
        assert geometry["radius"] == pytest.approx(0.05)

    def test_transform_matrices(self, centimeters):
        assert build_transform_matrix(tx=55)[3] == pytest.approx(0.55)
        assert build_absolute_translation_matrix(0, 0, 75)[11] == pytest.approx(0.75)


class TestOutputInCentimeters:
    def test_positions_report(self, centimeters):
        pos = InstancePositionInfo("Side", "i1", 0, 0, 0, 1.5, 10, 75, 0, 0, 0, 1.5, 10, 75)
        report = format_positions_report([pos])
        assert "1.500 cm W x 10.000 cm D x 75.000 cm H" in report
        assert '"' not in report

    def test_interference_report(self, centimeters):
        result = InterferenceResult(
            total_instances=2,
            total_pairs_checked=1,
            overlaps=[OverlapInfo("A", "a", "B", "b", 0.5, 10.0, 20.0, 100.0)],
        )
        report = format_interference_result(result)
        assert "X=0.500 cm" in report
        assert "100.000 cubic centimeters" in report
        assert "Move one part 0.500 cm along X" in report


class TestToolDescriptions:
    @pytest.mark.asyncio
    async def test_describe_the_configured_unit(self, centimeters):
        tools = {tool.name: tool for tool in await list_tools()}
        depth = tools["create_extrude"].inputSchema["properties"]["depth"]
        assert depth["description"] == "Extrude depth in centimeters"
        assert "centimeters" in tools["set_instance_position"].description
        assert not any("inch" in str(tool.model_dump()) for tool in tools.values())
