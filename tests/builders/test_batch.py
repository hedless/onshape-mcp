"""Tests for batch builder module."""

import pytest

from onshape_mcp.builders.batch import BatchBuilder


@pytest.fixture
def builder():
    return BatchBuilder(namespace="eABC123::mDEF456")


class TestRectExtrude:
    def test_basic_rect_extrude(self, builder):
        result = builder.rect_extrude(
            name="Test Box",
            plane="Front",
            corner1=(0, 0),
            corner2=(10, 5),
            depth=3.0,
        )

        assert result["btType"] == "BTFeatureDefinitionCall-1406"
        feature = result["feature"]
        assert feature["featureType"] == "rectExtrude"
        assert feature["name"] == "Test Box"
        assert feature["namespace"] == "eABC123::mDEF456"

        params = {p["parameterId"]: p for p in feature["parameters"]}
        assert params["name"]["value"] == "Test Box"
        assert params["sketchPlane"]["value"] == "Front"
        assert params["x1"]["expression"] == "0 in"
        assert params["y1"]["expression"] == "0 in"
        assert params["x2"]["expression"] == "10 in"
        assert params["y2"]["expression"] == "5 in"
        assert params["depth"]["expression"] == "3.0 in"
        assert params["operationType"]["value"] == "NEW"
        assert params["hasDraft"]["value"] is False

    def test_rect_extrude_with_draft(self, builder):
        result = builder.rect_extrude(
            name="Tapered",
            plane="Top",
            corner1=(-1, -1),
            corner2=(1, 1),
            depth=6.5,
            draft_angle=3.0,
            draft_pull_direction=True,
        )

        params = {p["parameterId"]: p for p in result["feature"]["parameters"]}
        assert params["hasDraft"]["value"] is True
        assert params["draftAngle"]["expression"] == "3.0 deg"
        assert params["draftPullDirection"]["value"] is True

    def test_rect_extrude_remove_operation(self, builder):
        result = builder.rect_extrude(
            name="Cavity",
            plane="Front",
            corner1=(1, 1),
            corner2=(9, 4),
            depth=2.5,
            operation_type="REMOVE",
        )

        params = {p["parameterId"]: p for p in result["feature"]["parameters"]}
        assert params["operationType"]["value"] == "REMOVE"

    def test_rect_extrude_no_draft_params_when_disabled(self, builder):
        result = builder.rect_extrude(
            name="No Draft",
            plane="Front",
            corner1=(0, 0),
            corner2=(5, 5),
            depth=1.0,
        )

        param_ids = [p["parameterId"] for p in result["feature"]["parameters"]]
        assert "draftAngle" not in param_ids
        assert "draftPullDirection" not in param_ids


class TestPolyExtrude:
    def test_triangle(self, builder):
        result = builder.poly_extrude(
            name="Triangle",
            plane="Front",
            vertices=[(0, 0), (5, 0), (2.5, 4)],
            depth=1.0,
        )

        feature = result["feature"]
        assert feature["featureType"] == "polyExtrude"
        params = {p["parameterId"]: p for p in feature["parameters"]}
        assert params["vertexCount"]["value"] == 3
        assert params["v1x"]["expression"] == "0 in"
        assert params["v3y"]["expression"] == "4 in"

    def test_trapezoid(self, builder):
        result = builder.poly_extrude(
            name="Speaker Bay",
            plane="Front",
            vertices=[(0, 0), (7.5, 0), (13.25, 27), (0, 27)],
            depth=21.5,
        )

        params = {p["parameterId"]: p for p in result["feature"]["parameters"]}
        assert params["vertexCount"]["value"] == 4
        assert params["v4x"]["expression"] == "0 in"
        assert params["v4y"]["expression"] == "27 in"

    def test_too_few_vertices_raises(self, builder):
        with pytest.raises(ValueError, match="3-8 vertices"):
            builder.poly_extrude(
                name="Line",
                plane="Front",
                vertices=[(0, 0), (5, 0)],
                depth=1.0,
            )

    def test_too_many_vertices_raises(self, builder):
        with pytest.raises(ValueError, match="3-8 vertices"):
            builder.poly_extrude(
                name="Nonagon",
                plane="Front",
                vertices=[(i, i) for i in range(9)],
                depth=1.0,
            )


class TestCabinetBox:
    def test_basic_cabinet(self, builder):
        result = builder.cabinet_box(
            name="Center Cabinet",
            width=27.0,
            height=27.0,
            depth=21.5,
            panel_thickness=0.75,
        )

        feature = result["feature"]
        assert feature["featureType"] == "cabinetBox"
        params = {p["parameterId"]: p for p in feature["parameters"]}
        assert params["width"]["expression"] == "27.0 in"
        assert params["height"]["expression"] == "27.0 in"
        assert params["depth"]["expression"] == "21.5 in"
        assert params["panelThickness"]["expression"] == "0.75 in"
        assert params["centeredX"]["value"] is True
        assert params["hasDivider"]["value"] is False
        assert params["hasShelf"]["value"] is False

    def test_cabinet_with_divider_and_shelf(self, builder):
        result = builder.cabinet_box(
            name="Full Cabinet",
            width=27.0,
            height=27.0,
            depth=21.5,
            panel_thickness=0.75,
            has_divider=True,
            has_shelf=True,
            shelf_height=13.5,
        )

        params = {p["parameterId"]: p for p in result["feature"]["parameters"]}
        assert params["hasDivider"]["value"] is True
        assert params["hasShelf"]["value"] is True
        assert params["shelfHeight"]["expression"] == "13.5 in"

    def test_cabinet_not_centered(self, builder):
        result = builder.cabinet_box(
            name="Off-center",
            width=10.0,
            height=10.0,
            depth=10.0,
            panel_thickness=0.5,
            centered_x=False,
        )

        params = {p["parameterId"]: p for p in result["feature"]["parameters"]}
        assert params["centeredX"]["value"] is False


class TestNamespace:
    def test_namespace_propagated(self):
        builder = BatchBuilder(namespace="e12345::m67890")
        result = builder.rect_extrude(
            name="Test",
            plane="Front",
            corner1=(0, 0),
            corner2=(1, 1),
            depth=1.0,
        )
        assert result["feature"]["namespace"] == "e12345::m67890"

    def test_different_namespace(self):
        builder = BatchBuilder(namespace="eAAA::mBBB")
        result = builder.cabinet_box(
            name="Test",
            width=1.0,
            height=1.0,
            depth=1.0,
            panel_thickness=0.1,
        )
        assert result["feature"]["namespace"] == "eAAA::mBBB"
