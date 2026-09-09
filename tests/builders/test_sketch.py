"""Unit tests for Sketch builder - Corrected for actual Onshape API structure."""

import math

import pytest
from onshape_mcp.builders.sketch import REFERENCE_PLANES, SketchBuilder, SketchPlane


class TestSketchPlane:
    """Test SketchPlane enum."""

    def test_sketch_plane_values(self):
        """Test that SketchPlane enum has correct values."""
        assert SketchPlane.FRONT.value == "Front"
        assert SketchPlane.TOP.value == "Top"
        assert SketchPlane.RIGHT.value == "Right"

    def test_sketch_plane_by_name(self):
        """Test accessing SketchPlane by name."""
        assert SketchPlane["FRONT"] == SketchPlane.FRONT
        assert SketchPlane["TOP"] == SketchPlane.TOP
        assert SketchPlane["RIGHT"] == SketchPlane.RIGHT


class TestSketchBuilder:
    """Test SketchBuilder functionality."""

    def test_initialization_with_defaults(self):
        """Test creating a sketch builder with default parameters."""
        sketch = SketchBuilder()

        assert sketch.name == "Sketch"
        assert sketch.plane == SketchPlane.FRONT
        assert sketch.entities == []
        assert sketch.constraints == []

    def test_initialization_with_custom_values(self):
        """Test creating a sketch builder with custom parameters."""
        sketch = SketchBuilder(name="MySketch", plane=SketchPlane.TOP)

        assert sketch.name == "MySketch"
        assert sketch.plane == SketchPlane.TOP

    def test_add_rectangle_basic(self):
        """Test adding a basic rectangle."""
        sketch = SketchBuilder()
        result = sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5))

        # Should return self for chaining
        assert result is sketch

        # Should create 4 line entities (bottom, right, top, left)
        assert len(sketch.entities) == 4

        # Verify each entity has proper Onshape API structure
        for entity in sketch.entities:
            assert entity["btType"] == "BTMSketchCurveSegment-155"
            assert entity["geometry"]["btType"] == "BTCurveGeometryLine-117"
            assert entity["isConstruction"] is False
            assert "entityId" in entity
            assert "startPointId" in entity
            assert "endPointId" in entity

    def test_add_rectangle_creates_constraints(self):
        """Test that adding rectangle creates geometric constraints."""
        sketch = SketchBuilder()
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5))

        # Should create multiple constraints (perpendicular, parallel, horizontal, coincident)
        assert len(sketch.constraints) > 0

        # All constraints should have proper Onshape API structure
        for constraint in sketch.constraints:
            assert constraint["btType"] == "BTMSketchConstraint-2"
            assert "constraintType" in constraint
            assert "entityId" in constraint
            assert "parameters" in constraint

    def test_add_rectangle_with_variable_width(self):
        """Test adding rectangle with width variable."""
        sketch = SketchBuilder()
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5), variable_width="box_width")

        # Should have additional LENGTH constraint for width
        length_constraints = [c for c in sketch.constraints if c["constraintType"] == "LENGTH"]
        assert len(length_constraints) == 1

        # Check the constraint uses the variable
        width_constraint = length_constraints[0]
        params = width_constraint["parameters"]
        quantity_param = next(p for p in params if p["btType"] == "BTMParameterQuantity-147")
        assert quantity_param["expression"] == "#box_width"

    def test_add_rectangle_with_variable_height(self):
        """Test adding rectangle with height variable."""
        sketch = SketchBuilder()
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5), variable_height="box_height")

        # Should have additional LENGTH constraint for height
        length_constraints = [c for c in sketch.constraints if c["constraintType"] == "LENGTH"]
        assert len(length_constraints) == 1

        # Check the constraint uses the variable
        height_constraint = length_constraints[0]
        params = height_constraint["parameters"]
        quantity_param = next(p for p in params if p["btType"] == "BTMParameterQuantity-147")
        assert quantity_param["expression"] == "#box_height"

    def test_add_rectangle_with_both_variables(self):
        """Test adding rectangle with both width and height variables."""
        sketch = SketchBuilder()
        sketch.add_rectangle(
            corner1=(0, 0), corner2=(10, 5), variable_width="width", variable_height="height"
        )

        # Should have 2 LENGTH constraints
        length_constraints = [c for c in sketch.constraints if c["constraintType"] == "LENGTH"]
        assert len(length_constraints) == 2

        # Check both variables are used
        expressions = []
        for constraint in length_constraints:
            params = constraint["parameters"]
            quantity_param = next(p for p in params if p["btType"] == "BTMParameterQuantity-147")
            expressions.append(quantity_param["expression"])

        assert "#width" in expressions
        assert "#height" in expressions

    def test_method_chaining(self):
        """Test that builder methods can be chained."""
        sketch = SketchBuilder(name="Chained").add_rectangle((0, 0), (10, 5))

        # Should have 4 rectangle lines
        assert len(sketch.entities) == 4
        assert sketch.name == "Chained"

    def test_build_requires_plane_id(self):
        """Test that build() requires plane_id to be provided."""
        sketch = SketchBuilder(name="TestSketch", plane=SketchPlane.FRONT)
        sketch.add_rectangle((0, 0), (5, 5))

        # Should raise error if no plane_id provided
        with pytest.raises(ValueError, match="plane_id must be provided"):
            sketch.build()

    def test_build_with_plane_id(self):
        """Test that build() works when plane_id is provided."""
        sketch = SketchBuilder(name="TestSketch", plane=SketchPlane.FRONT)
        sketch.add_rectangle((0, 0), (5, 5))

        result = sketch.build(plane_id="test_plane_id")

        # Verify top-level structure
        assert "feature" in result

        feature = result["feature"]
        assert feature["btType"] == "BTMSketch-151"
        assert feature["name"] == "TestSketch"
        assert "parameters" in feature
        assert "constraints" in feature
        assert "entities" in feature

        # Verify plane parameter
        assert len(feature["parameters"]) > 0
        plane_param = feature["parameters"][0]
        assert plane_param["parameterId"] == "sketchPlane"
        assert plane_param["queries"][0]["deterministicIds"] == ["test_plane_id"]

    def test_build_includes_entities_and_constraints(self):
        """Test that build() includes all entities and constraints."""
        sketch = SketchBuilder(plane_id="test_plane")
        sketch.add_rectangle((0, 0), (10, 5), variable_width="w", variable_height="h")

        result = sketch.build()

        feature = result["feature"]
        # 4 rectangle lines
        assert len(feature["entities"]) == 4
        # Multiple constraints (geometric + 2 dimensional)
        assert len(feature["constraints"]) > 2


class TestSketchBuilderCircle:
    """Test add_circle functionality."""

    def test_add_circle_returns_self(self):
        sketch = SketchBuilder()
        result = sketch.add_circle(center=(5, 5), radius=3)
        assert result is sketch

    def test_add_circle_creates_two_arcs(self):
        sketch = SketchBuilder()
        sketch.add_circle(center=(5, 5), radius=3)
        assert len(sketch.entities) == 2

        for entity in sketch.entities:
            assert entity["btType"] == "BTMSketchCurveSegment-155"
            assert entity["geometry"]["btType"] == "BTCurveGeometryCircle-115"
            assert entity["isConstruction"] is False

    def test_add_circle_arcs_form_full_circle(self):
        sketch = SketchBuilder()
        sketch.add_circle(center=(0, 0), radius=1)

        arc1, arc2 = sketch.entities
        assert arc1["startParam"] == 0.0
        assert abs(arc1["endParam"] - math.pi) < 1e-10
        assert abs(arc2["startParam"] - math.pi) < 1e-10
        assert abs(arc2["endParam"] - 2.0 * math.pi) < 1e-10

    def test_add_circle_converts_to_meters(self):
        sketch = SketchBuilder()
        sketch.add_circle(center=(1.0, 2.0), radius=3.0)

        geo = sketch.entities[0]["geometry"]
        assert abs(geo["xCenter"] - 1.0 * 0.0254) < 1e-10
        assert abs(geo["yCenter"] - 2.0 * 0.0254) < 1e-10
        assert abs(geo["radius"] - 3.0 * 0.0254) < 1e-10

    def test_add_circle_adds_coincident_constraints(self):
        sketch = SketchBuilder()
        sketch.add_circle(center=(0, 0), radius=1)
        assert len(sketch.constraints) == 2
        assert sketch.constraints[0]["constraintType"] == "COINCIDENT"
        assert sketch.constraints[1]["constraintType"] == "COINCIDENT"

    def test_add_circle_construction(self):
        sketch = SketchBuilder()
        sketch.add_circle(center=(0, 0), radius=1, is_construction=True)
        assert sketch.entities[0]["isConstruction"] is True
        assert sketch.entities[1]["isConstruction"] is True


class TestSketchBuilderArc:
    """Test add_arc functionality."""

    def test_add_arc_returns_self(self):
        sketch = SketchBuilder()
        result = sketch.add_arc(center=(0, 0), radius=5, start_angle=0, end_angle=90)
        assert result is sketch

    def test_add_arc_creates_entity(self):
        sketch = SketchBuilder()
        sketch.add_arc(center=(1, 2), radius=3, start_angle=0, end_angle=180)
        assert len(sketch.entities) == 1

        entity = sketch.entities[0]
        assert entity["btType"] == "BTMSketchCurveSegment-155"
        assert entity["geometry"]["btType"] == "BTCurveGeometryCircle-115"

    def test_add_arc_converts_angles_to_radians(self):
        sketch = SketchBuilder()
        sketch.add_arc(center=(0, 0), radius=1, start_angle=45, end_angle=135)

        entity = sketch.entities[0]
        assert abs(entity["startParam"] - math.radians(45)) < 1e-10
        assert abs(entity["endParam"] - math.radians(135)) < 1e-10

    def test_add_arc_construction(self):
        sketch = SketchBuilder()
        sketch.add_arc(center=(0, 0), radius=1, is_construction=True)
        assert sketch.entities[0]["isConstruction"] is True


class TestSketchBuilderLine:
    """Test add_line functionality."""

    def test_add_line_returns_self(self):
        sketch = SketchBuilder()
        result = sketch.add_line(start=(0, 0), end=(10, 10))
        assert result is sketch

    def test_add_line_creates_entity(self):
        sketch = SketchBuilder()
        sketch.add_line(start=(0, 0), end=(10, 0))
        assert len(sketch.entities) == 1

        entity = sketch.entities[0]
        assert entity["btType"] == "BTMSketchCurveSegment-155"
        assert entity["geometry"]["btType"] == "BTCurveGeometryLine-117"
        assert entity["isConstruction"] is False

    def test_add_line_direction_horizontal(self):
        sketch = SketchBuilder()
        sketch.add_line(start=(0, 0), end=(10, 0))

        geo = sketch.entities[0]["geometry"]
        assert abs(geo["dirX"] - 1.0) < 1e-10
        assert abs(geo["dirY"] - 0.0) < 1e-10

    def test_add_line_direction_vertical(self):
        sketch = SketchBuilder()
        sketch.add_line(start=(0, 0), end=(0, 5))

        geo = sketch.entities[0]["geometry"]
        assert abs(geo["dirX"] - 0.0) < 1e-10
        assert abs(geo["dirY"] - 1.0) < 1e-10

    def test_add_line_construction(self):
        sketch = SketchBuilder()
        sketch.add_line(start=(0, 0), end=(10, 10), is_construction=True)
        assert sketch.entities[0]["isConstruction"] is True

    def test_add_line_zero_length_raises(self):
        sketch = SketchBuilder()
        with pytest.raises(ValueError, match="Line start and end points must be different"):
            sketch.add_line(start=(5, 5), end=(5, 5))


class TestSketchBuilderPolygon:
    """Test add_polygon functionality."""

    def test_add_polygon_returns_self(self):
        sketch = SketchBuilder()
        result = sketch.add_polygon(center=(0, 0), sides=6, radius=5)
        assert result is sketch

    def test_add_polygon_triangle(self):
        sketch = SketchBuilder()
        sketch.add_polygon(center=(0, 0), sides=3, radius=5)
        assert len(sketch.entities) == 3

    def test_add_polygon_hexagon(self):
        sketch = SketchBuilder()
        sketch.add_polygon(center=(0, 0), sides=6, radius=5)
        assert len(sketch.entities) == 6

    def test_add_polygon_all_lines(self):
        sketch = SketchBuilder()
        sketch.add_polygon(center=(0, 0), sides=4, radius=5)
        for entity in sketch.entities:
            assert entity["geometry"]["btType"] == "BTCurveGeometryLine-117"

    def test_add_polygon_less_than_3_sides_raises(self):
        sketch = SketchBuilder()
        with pytest.raises(ValueError, match="Polygon must have at least 3 sides"):
            sketch.add_polygon(center=(0, 0), sides=2, radius=5)

    def test_add_polygon_construction(self):
        sketch = SketchBuilder()
        sketch.add_polygon(center=(0, 0), sides=4, radius=5, is_construction=True)
        for entity in sketch.entities:
            assert entity["isConstruction"] is True

    def test_mixed_entities(self):
        """Test combining different entity types in one sketch."""
        sketch = SketchBuilder(plane_id="plane1")
        sketch.add_rectangle((0, 0), (10, 5))
        sketch.add_circle((5, 2.5), 1)
        sketch.add_line((0, 0), (10, 5))

        # 4 rect lines + 2 circle arcs + 1 line
        assert len(sketch.entities) == 7

        result = sketch.build()
        assert len(result["feature"]["entities"]) == 7


class TestSketchBuilderPolyline:
    """Test add_polyline functionality."""

    def test_add_polyline_returns_self(self):
        sketch = SketchBuilder()
        result = sketch.add_polyline(points=[(0, 0), (10, 0), (10, 5)])
        assert result is sketch

    def test_add_polyline_triangle(self):
        """Closed triangle: 3 points -> 3 line entities + 3 COINCIDENT constraints."""
        sketch = SketchBuilder()
        sketch.add_polyline(points=[(0, 0), (10, 0), (5, 8)])

        assert len(sketch.entities) == 3
        for entity in sketch.entities:
            assert entity["geometry"]["btType"] == "BTCurveGeometryLine-117"

        coincident = [c for c in sketch.constraints if c["constraintType"] == "COINCIDENT"]
        assert len(coincident) == 3

    def test_add_polyline_trapezoid(self):
        """Closed trapezoid: 4 points -> 4 lines + 4 COINCIDENT constraints."""
        sketch = SketchBuilder()
        sketch.add_polyline(points=[(0, 0), (8, 0), (13.25, 27), (0, 27)])

        assert len(sketch.entities) == 4

        coincident = [c for c in sketch.constraints if c["constraintType"] == "COINCIDENT"]
        assert len(coincident) == 4

    def test_add_polyline_open(self):
        """Open polyline: 3 points -> 2 lines + 2 COINCIDENT constraints (no closing segment)."""
        sketch = SketchBuilder()
        sketch.add_polyline(points=[(0, 0), (5, 0), (10, 5)], closed=False)

        assert len(sketch.entities) == 2

        coincident = [c for c in sketch.constraints if c["constraintType"] == "COINCIDENT"]
        # Only interior vertex constraint (line1.end -> line2.start)
        assert len(coincident) == 1

    def test_add_polyline_closed_too_few_points_raises(self):
        sketch = SketchBuilder()
        with pytest.raises(ValueError, match="at least 3 points"):
            sketch.add_polyline(points=[(0, 0), (5, 5)], closed=True)

    def test_add_polyline_open_too_few_points_raises(self):
        sketch = SketchBuilder()
        with pytest.raises(ValueError, match="at least 2 points"):
            sketch.add_polyline(points=[(0, 0)], closed=False)

    def test_add_polyline_coordinates_correct(self):
        """Verify line start/end match the given vertices."""
        sketch = SketchBuilder()
        pts = [(0, 0), (10, 0), (10, 5)]
        sketch.add_polyline(points=pts, closed=True)

        def to_meters(v):
            return v * 0.0254

        # Check first line: (0,0) -> (10,0)
        geo0 = sketch.entities[0]["geometry"]
        assert abs(geo0["pntX"] - to_meters(0)) < 1e-10
        assert abs(geo0["pntY"] - to_meters(0)) < 1e-10

        # Check second line: (10,0) -> (10,5)
        geo1 = sketch.entities[1]["geometry"]
        assert abs(geo1["pntX"] - to_meters(10)) < 1e-10
        assert abs(geo1["pntY"] - to_meters(0)) < 1e-10

        # Check third (closing) line: (10,5) -> (0,0)
        geo2 = sketch.entities[2]["geometry"]
        assert abs(geo2["pntX"] - to_meters(10)) < 1e-10
        assert abs(geo2["pntY"] - to_meters(5)) < 1e-10

    def test_add_polyline_constraints_connect_consecutive_lines(self):
        """Verify COINCIDENT constraints connect line[i].end to line[i+1].start."""
        sketch = SketchBuilder()
        sketch.add_polyline(points=[(0, 0), (10, 0), (10, 5)], closed=True)

        coincident = [c for c in sketch.constraints if c["constraintType"] == "COINCIDENT"]
        assert len(coincident) == 3

        # First constraint: line1.end -> line2.start
        c0_params = coincident[0]["parameters"]
        assert c0_params[0]["value"] == sketch.entities[0]["endPointId"]
        assert c0_params[1]["value"] == sketch.entities[1]["startPointId"]

        # Second constraint: line2.end -> line3.start
        c1_params = coincident[1]["parameters"]
        assert c1_params[0]["value"] == sketch.entities[1]["endPointId"]
        assert c1_params[1]["value"] == sketch.entities[2]["startPointId"]

        # Third (closing) constraint: line3.end -> line1.start
        c2_params = coincident[2]["parameters"]
        assert c2_params[0]["value"] == sketch.entities[2]["endPointId"]
        assert c2_params[1]["value"] == sketch.entities[0]["startPointId"]

    def test_add_polyline_builds_valid_json(self):
        """Full build() produces valid sketch with all entities."""
        sketch = SketchBuilder(plane_id="test_plane")
        sketch.add_polyline(points=[(0, 0), (8, 0), (13.25, 27), (0, 27)])

        result = sketch.build()
        feature = result["feature"]

        assert feature["btType"] == "BTMSketch-151"
        assert len(feature["entities"]) == 4
        assert len(feature["constraints"]) == 4

    def test_add_polyline_construction(self):
        sketch = SketchBuilder()
        sketch.add_polyline(points=[(0, 0), (5, 0), (5, 5)], is_construction=True)
        for entity in sketch.entities:
            assert entity["isConstruction"] is True

    def test_add_polyline_with_variable_lengths(self):
        """Test that variable_lengths adds LENGTH constraints per segment."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_polyline(
            points=[(0, 0), (10, 0), (10, 5)],
            closed=False,
            variable_lengths=["#width", None],
        )
        length_constraints = [c for c in sketch.constraints if c["constraintType"] == "LENGTH"]
        assert len(length_constraints) == 1
        expr = next(
            p
            for p in length_constraints[0]["parameters"]
            if p["btType"] == "BTMParameterQuantity-147"
        )
        assert expr["expression"] == "#width"

    def test_add_polyline_variable_lengths_skips_none(self):
        """Test that None entries in variable_lengths produce no constraint."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_polyline(
            points=[(0, 0), (5, 0), (5, 5)],
            closed=True,
            variable_lengths=[None, None, None],
        )
        length_constraints = [c for c in sketch.constraints if c["constraintType"] == "LENGTH"]
        assert len(length_constraints) == 0

    def test_add_polyline_variable_lengths_wrong_count_raises(self):
        """Test that wrong length of variable_lengths raises ValueError."""
        sketch = SketchBuilder(plane_id="test")
        with pytest.raises(ValueError, match="variable_lengths must have"):
            sketch.add_polyline(
                points=[(0, 0), (5, 0), (5, 5)],
                closed=True,
                variable_lengths=["#a", "#b"],  # 2 but need 3
            )

    def test_add_polyline_with_anchors(self):
        """Test that anchor_x/anchor_y add DISTANCE constraints."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_polyline(
            points=[(0, 0), (5, 0), (5, 5)],
            anchor_x="5 in",
            anchor_y="#offset",
        )
        distance_constraints = [c for c in sketch.constraints if c["constraintType"] == "DISTANCE"]
        assert len(distance_constraints) == 2

        # Check reference planes match Front plane mapping
        for dc in distance_constraints:
            ext_param = next(p for p in dc["parameters"] if p.get("parameterId") == "externalFirst")
            plane_id = ext_param["queries"][0]["deterministicIds"][0]
            assert plane_id in ("JEC", "JDC")  # Right or Top for Front plane

    def test_add_polyline_with_horizontal_edges(self):
        """Test horizontal_edges adds HORIZONTAL constraints to specified segments."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_polyline(
            points=[(0, 0), (8, 0), (13, 27), (0, 27)],
            horizontal_edges=[0, 2],
        )
        h_constraints = [c for c in sketch.constraints if c["constraintType"] == "HORIZONTAL"]
        assert len(h_constraints) == 2

    def test_add_polyline_with_vertical_edges(self):
        """Test vertical_edges adds VERTICAL constraints to specified segments."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_polyline(
            points=[(0, 0), (8, 0), (13, 27), (0, 27)],
            vertical_edges=[3],
        )
        v_constraints = [c for c in sketch.constraints if c["constraintType"] == "VERTICAL"]
        assert len(v_constraints) == 1

    def test_add_polyline_with_both_orientation_constraints(self):
        """Test combining horizontal and vertical edge constraints."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_polyline(
            points=[(0, 0), (8, 0), (13, 27), (0, 27)],
            horizontal_edges=[0, 2],
            vertical_edges=[3],
        )
        h_constraints = [c for c in sketch.constraints if c["constraintType"] == "HORIZONTAL"]
        v_constraints = [c for c in sketch.constraints if c["constraintType"] == "VERTICAL"]
        assert len(h_constraints) == 2
        assert len(v_constraints) == 1


class TestReferencePlanes:
    """Test REFERENCE_PLANES mapping."""

    def test_front_plane_references(self):
        assert REFERENCE_PLANES[SketchPlane.FRONT] == {"x": "JEC", "y": "JDC"}

    def test_top_plane_references(self):
        assert REFERENCE_PLANES[SketchPlane.TOP] == {"x": "JEC", "y": "JCC"}

    def test_right_plane_references(self):
        assert REFERENCE_PLANES[SketchPlane.RIGHT] == {"x": "JCC", "y": "JDC"}


class TestSketchConstraintMethods:
    """Test public constraint methods on SketchBuilder."""

    def test_add_horizontal_constraint(self):
        """Test HORIZONTAL constraint JSON structure."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_horizontal_constraint("line.1")

        assert len(sketch.constraints) == 1
        c = sketch.constraints[0]
        assert c["btType"] == "BTMSketchConstraint-2"
        assert c["constraintType"] == "HORIZONTAL"
        assert c["parameters"][0]["value"] == "line.1"
        assert c["parameters"][0]["parameterId"] == "localFirst"

    def test_add_vertical_constraint(self):
        """Test VERTICAL constraint JSON structure."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_vertical_constraint("line.1")

        assert len(sketch.constraints) == 1
        c = sketch.constraints[0]
        assert c["btType"] == "BTMSketchConstraint-2"
        assert c["constraintType"] == "VERTICAL"
        assert c["parameters"][0]["value"] == "line.1"
        assert c["parameters"][0]["parameterId"] == "localFirst"

    def test_add_length_constraint(self):
        """Test LENGTH constraint with expression."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_length_constraint("line.1", "10 in")

        assert len(sketch.constraints) == 1
        c = sketch.constraints[0]
        assert c["constraintType"] == "LENGTH"
        expr = next(p for p in c["parameters"] if p["btType"] == "BTMParameterQuantity-147")
        assert expr["expression"] == "10 in"

    def test_add_length_constraint_with_variable(self):
        """Test LENGTH constraint with variable reference."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_length_constraint("rect.1.bottom", "#panel_width")

        c = sketch.constraints[0]
        expr = next(p for p in c["parameters"] if p["btType"] == "BTMParameterQuantity-147")
        assert expr["expression"] == "#panel_width"

    def test_add_distance_constraint(self):
        """Test DISTANCE constraint with reference plane."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_distance_constraint("rect.1.left", "#width/2", "JEC")

        assert len(sketch.constraints) == 1
        c = sketch.constraints[0]
        assert c["constraintType"] == "DISTANCE"

        # Check externalFirst query
        ext_param = next(p for p in c["parameters"] if p.get("parameterId") == "externalFirst")
        assert ext_param["queries"][0]["deterministicIds"] == ["JEC"]

        # Check localSecond
        local_param = next(p for p in c["parameters"] if p.get("parameterId") == "localSecond")
        assert local_param["value"] == "rect.1.left"

        # Check length expression
        length_param = next(p for p in c["parameters"] if p.get("parameterId") == "length")
        assert length_param["expression"] == "#width/2"

    def test_add_fix_constraint(self):
        """Test FIX constraint."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_fix_constraint("line.1.start")

        assert len(sketch.constraints) == 1
        c = sketch.constraints[0]
        assert c["constraintType"] == "FIX"
        assert c["parameters"][0]["value"] == "line.1.start"

    def test_add_generic_constraint_two_entities(self):
        """Test generic constraint with two entities (e.g., EQUAL)."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_constraint("EQUAL", "line.1", "line.2")

        c = sketch.constraints[0]
        assert c["constraintType"] == "EQUAL"
        assert c["parameters"][0]["value"] == "line.1"
        assert c["parameters"][0]["parameterId"] == "localFirst"
        assert c["parameters"][1]["value"] == "line.2"
        assert c["parameters"][1]["parameterId"] == "localSecond"

    def test_add_generic_constraint_single_entity(self):
        """Test generic constraint with one entity (e.g., HORIZONTAL)."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_constraint("HORIZONTAL", "line.1")

        c = sketch.constraints[0]
        assert c["constraintType"] == "HORIZONTAL"
        assert len(c["parameters"]) == 1
        assert c["parameters"][0]["value"] == "line.1"

    def test_constraint_methods_return_self(self):
        """Test that all constraint methods return self for chaining."""
        sketch = SketchBuilder(plane_id="test")
        assert sketch.add_vertical_constraint("l.1") is sketch
        assert sketch.add_length_constraint("l.1", "5 in") is sketch
        assert sketch.add_distance_constraint("l.1", "3 in", "JEC") is sketch
        assert sketch.add_fix_constraint("l.1.start") is sketch
        assert sketch.add_constraint("EQUAL", "l.1", "l.2") is sketch


class TestSketchBuilderRectangleConstraints:
    """Test enhanced rectangle constraints (VERTICAL + anchors)."""

    def test_rectangle_includes_vertical_constraint(self):
        """Test that rectangle now includes VERTICAL on left side."""
        sketch = SketchBuilder(plane_id="test")
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5))

        vertical = [c for c in sketch.constraints if c["constraintType"] == "VERTICAL"]
        assert len(vertical) == 1
        # Should be on the left line
        assert "left" in vertical[0]["entityId"] or "left" in vertical[0]["parameters"][0]["value"]

    def test_rectangle_with_anchors(self):
        """Test that anchorX/anchorY create DISTANCE constraints."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5), anchor_x="5 in", anchor_y="3 in")

        distance = [c for c in sketch.constraints if c["constraintType"] == "DISTANCE"]
        assert len(distance) == 2

    def test_rectangle_anchors_use_correct_planes_front(self):
        """Test that Front plane sketch uses Right (JEC) and Top (JDC) as references."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5), anchor_x="5 in", anchor_y="3 in")

        distance = [c for c in sketch.constraints if c["constraintType"] == "DISTANCE"]
        plane_ids = set()
        for dc in distance:
            ext = next(p for p in dc["parameters"] if p.get("parameterId") == "externalFirst")
            plane_ids.add(ext["queries"][0]["deterministicIds"][0])
        assert plane_ids == {"JEC", "JDC"}

    def test_rectangle_anchors_use_correct_planes_top(self):
        """Test that Top plane sketch uses Right (JEC) and Front (JCC) as references."""
        sketch = SketchBuilder(plane=SketchPlane.TOP, plane_id="test")
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5), anchor_x="5 in", anchor_y="3 in")

        distance = [c for c in sketch.constraints if c["constraintType"] == "DISTANCE"]
        plane_ids = set()
        for dc in distance:
            ext = next(p for p in dc["parameters"] if p.get("parameterId") == "externalFirst")
            plane_ids.add(ext["queries"][0]["deterministicIds"][0])
        assert plane_ids == {"JEC", "JCC"}

    def test_rectangle_without_anchors_no_distance(self):
        """Test that no anchors means no DISTANCE constraints."""
        sketch = SketchBuilder(plane=SketchPlane.FRONT, plane_id="test")
        sketch.add_rectangle(corner1=(0, 0), corner2=(10, 5))

        distance = [c for c in sketch.constraints if c["constraintType"] == "DISTANCE"]
        assert len(distance) == 0
