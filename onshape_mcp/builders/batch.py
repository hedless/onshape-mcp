"""Batch builder for invoking custom FeatureScript features via the API.

Generates the addFeature JSON needed to invoke custom features defined in
a Feature Studio. Each call creates one feature that internally performs
multiple sketch + extrude operations, drastically reducing API call count.

Typical savings:
- Cabinet box with cavity + divider + shelf: 8 calls → 1
- Rectangular panel: 2 calls → 1
- Polygon extrude: 2 calls → 1
"""

from typing import Any, Dict, List, Optional, Tuple


def _length_param(param_id: str, value: float, expression: Optional[str] = None) -> Dict[str, Any]:
    """Create a length quantity parameter."""
    return {
        "btType": "BTMParameterQuantity-147",
        "isInteger": False,
        "value": 0.0,
        "units": "",
        "expression": expression or f"{value} in",
        "parameterId": param_id,
        "parameterName": "",
        "libraryRelationType": "NONE",
    }


def _angle_param(param_id: str, value: float) -> Dict[str, Any]:
    """Create an angle quantity parameter."""
    return {
        "btType": "BTMParameterQuantity-147",
        "isInteger": False,
        "value": 0.0,
        "units": "",
        "expression": f"{value} deg",
        "parameterId": param_id,
        "parameterName": "",
        "libraryRelationType": "NONE",
    }


def _string_param(param_id: str, value: str) -> Dict[str, Any]:
    """Create a string parameter."""
    return {
        "btType": "BTMParameterString-149",
        "value": value,
        "parameterId": param_id,
        "parameterName": "",
        "libraryRelationType": "NONE",
    }


def _boolean_param(param_id: str, value: bool) -> Dict[str, Any]:
    """Create a boolean parameter."""
    return {
        "btType": "BTMParameterBoolean-144",
        "value": value,
        "parameterId": param_id,
        "parameterName": "",
        "libraryRelationType": "NONE",
    }


def _enum_param(param_id: str, enum_name: str, value: str) -> Dict[str, Any]:
    """Create an enum parameter."""
    return {
        "btType": "BTMParameterEnum-145",
        "namespace": "",
        "enumName": enum_name,
        "value": value,
        "parameterId": param_id,
        "parameterName": "",
        "libraryRelationType": "NONE",
    }


def _integer_param(param_id: str, value: int) -> Dict[str, Any]:
    """Create an integer parameter."""
    return {
        "btType": "BTMParameterQuantity-147",
        "isInteger": True,
        "value": value,
        "units": "",
        "expression": str(value),
        "parameterId": param_id,
        "parameterName": "",
        "libraryRelationType": "NONE",
    }


def _wrap_feature(
    feature_type: str,
    name: str,
    namespace: str,
    parameters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Wrap parameters in the BTFeatureDefinitionCall-1406 envelope.

    Args:
        feature_type: FeatureScript feature type name (e.g., 'rectExtrude')
        name: Display name for the feature
        namespace: Feature Studio namespace reference (e.g., 'e{eid}::m{mid}')
        parameters: List of parameter definitions
    """
    return {
        "btType": "BTFeatureDefinitionCall-1406",
        "feature": {
            "btType": "BTMFeature-134",
            "featureType": feature_type,
            "name": name,
            "namespace": namespace,
            "suppressed": False,
            "parameters": parameters,
            "returnAfterSubfeatures": False,
            "subFeatures": [],
        },
    }


class BatchBuilder:
    """Builds addFeature JSON for custom FeatureScript batch operations.

    Each method returns a feature definition dict that can be passed directly
    to the Part Studio addFeature API endpoint.

    Args:
        namespace: The Feature Studio namespace for custom features.
            Format: 'e{elementId}::m{microversionId}'
            Get this from get_feature_studio_specs or by inspecting
            an existing custom feature in the feature list.
    """

    def __init__(self, namespace: str):
        self.namespace = namespace

    def rect_extrude(
        self,
        name: str,
        plane: str,
        corner1: Tuple[float, float],
        corner2: Tuple[float, float],
        depth: float,
        operation_type: str = "NEW",
        draft_angle: Optional[float] = None,
        draft_pull_direction: bool = False,
    ) -> Dict[str, Any]:
        """Build a rectExtrude feature (rectangle sketch + extrude).

        Args:
            name: Feature name
            plane: Sketch plane ("Front", "Top", "Right")
            corner1: First corner (x, y) in inches
            corner2: Second corner (x, y) in inches
            depth: Extrude depth in inches
            operation_type: "NEW", "ADD", or "REMOVE"
            draft_angle: Optional draft angle in degrees
            draft_pull_direction: Draft direction (False=inward, True=outward)

        Returns:
            Feature definition for addFeature API
        """
        has_draft = draft_angle is not None

        params = [
            _string_param("name", name),
            _string_param("sketchPlane", plane),
            _length_param("x1", corner1[0]),
            _length_param("y1", corner1[1]),
            _length_param("x2", corner2[0]),
            _length_param("y2", corner2[1]),
            _length_param("depth", depth),
            _enum_param("operationType", "NewBodyOperationType", operation_type),
            _boolean_param("hasDraft", has_draft),
        ]

        if has_draft:
            params.append(_angle_param("draftAngle", draft_angle))
            params.append(_boolean_param("draftPullDirection", draft_pull_direction))

        return _wrap_feature("rectExtrude", name, self.namespace, params)

    def poly_extrude(
        self,
        name: str,
        plane: str,
        vertices: List[Tuple[float, float]],
        depth: float,
        operation_type: str = "NEW",
    ) -> Dict[str, Any]:
        """Build a polyExtrude feature (polygon sketch + extrude).

        Args:
            name: Feature name
            plane: Sketch plane ("Front", "Top", "Right")
            vertices: List of (x, y) vertices in inches (3-8 vertices)
            depth: Extrude depth in inches
            operation_type: "NEW", "ADD", or "REMOVE"

        Returns:
            Feature definition for addFeature API
        """
        if len(vertices) < 3 or len(vertices) > 8:
            raise ValueError("polyExtrude supports 3-8 vertices")

        params = [
            _string_param("name", name),
            _string_param("sketchPlane", plane),
            _integer_param("vertexCount", len(vertices)),
        ]

        # Add vertex coordinates
        for i, (x, y) in enumerate(vertices):
            params.append(_length_param(f"v{i + 1}x", x))
            params.append(_length_param(f"v{i + 1}y", y))

        params.extend(
            [
                _length_param("depth", depth),
                _enum_param("operationType", "NewBodyOperationType", operation_type),
            ]
        )

        return _wrap_feature("polyExtrude", name, self.namespace, params)

    def cabinet_box(
        self,
        name: str,
        width: float,
        height: float,
        depth: float,
        panel_thickness: float,
        centered_x: bool = True,
        has_divider: bool = False,
        has_shelf: bool = False,
        shelf_height: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Build a cabinetBox feature (shell + cavity + divider + shelf).

        Creates a complete cabinet box in a single API call. Replaces
        what would normally be 4-8 separate sketch+extrude operations.

        Args:
            name: Feature name
            width: Total cabinet width in inches
            height: Total cabinet height in inches
            depth: Total cabinet depth in inches
            panel_thickness: Wall/panel thickness in inches
            centered_x: Center the cabinet on X axis
            has_divider: Add vertical center divider
            has_shelf: Add horizontal shelf
            shelf_height: Height of shelf from bottom (required if has_shelf)

        Returns:
            Feature definition for addFeature API
        """
        params = [
            _string_param("name", name),
            _length_param("width", width),
            _length_param("height", height),
            _length_param("depth", depth),
            _length_param("panelThickness", panel_thickness),
            _boolean_param("centeredX", centered_x),
            _boolean_param("hasDivider", has_divider),
            _boolean_param("hasShelf", has_shelf),
        ]

        if has_shelf and shelf_height is not None:
            params.append(_length_param("shelfHeight", shelf_height))

        return _wrap_feature("cabinetBox", name, self.namespace, params)
