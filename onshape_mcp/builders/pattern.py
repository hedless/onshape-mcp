"""Pattern feature builders for Onshape."""

from enum import Enum
from typing import Any, Dict, List, Optional

from ..units import length_expression
from .axis_helper import FACE_QUERY_FOR_DIRECTION, normalize_axis


class PatternType(Enum):
    """Pattern entity type."""

    PART = "PART"
    FEATURE = "FEATURE"
    FACE = "FACE"


class LinearPatternBuilder:
    """Builder for creating Onshape linear (feature) pattern features."""

    def __init__(
        self,
        name: str = "Linear pattern",
        distance: float = 1.0,
        count: int = 2,
    ):
        """Initialize linear pattern builder.

        Args:
            name: Name of the pattern feature
            distance: Spacing between instances in the configured length unit
            count: Total number of instances including the original
        """
        self.name = name
        self.distance = distance
        self.count = count
        self.distance_variable: Optional[str] = None
        self.feature_queries: List[str] = []
        self.direction_axis = "X"
        self.reapply_features = False

    def set_distance(
        self, distance: float, variable_name: Optional[str] = None
    ) -> "LinearPatternBuilder":
        """Set the distance between pattern instances."""
        self.distance = distance
        self.distance_variable = variable_name
        return self

    def set_count(self, count: int) -> "LinearPatternBuilder":
        """Set the number of pattern instances (including the original)."""
        self.count = count
        return self

    def add_feature(self, feature_id: str) -> "LinearPatternBuilder":
        """Add a feature to pattern by its deterministic ID."""
        self.feature_queries.append(feature_id)
        return self

    def set_reapply_features(self, reapply: bool = True) -> "LinearPatternBuilder":
        """Re-run the patterned features per instance ("Reapply features" in the UI).

        Onshape's default copies the features' resulting bodies. If those bodies were
        modified by later features (fillet, chamfer, boolean...), regeneration fails
        with PATTERN_SWITCH_TO_PER_INSTANCE; enabling this makes each instance re-execute
        the original features instead.
        """
        self.reapply_features = reapply
        return self

    def set_direction(self, axis: str) -> "LinearPatternBuilder":
        """Set the pattern direction axis ("X", "Y", or "Z")."""
        self.direction_axis = normalize_axis(axis)
        return self

    def _build_direction_query(self) -> Dict[str, Any]:
        """Direction is a default-plane face; the pattern uses its normal."""
        return {
            "btType": "BTMParameterQueryList-148",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "queryString": FACE_QUERY_FOR_DIRECTION[normalize_axis(self.direction_axis)],
                }
            ],
            "parameterId": "directionOne",
            "parameterName": "",
        }

    def build(self) -> Dict[str, Any]:
        """Build the linear pattern feature JSON.

        Raises:
            ValueError: If no features have been added
        """
        if not self.feature_queries:
            raise ValueError("At least one feature must be added")

        distance_expression = (
            f"#{self.distance_variable}"
            if self.distance_variable
            else length_expression(self.distance)
        )

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "linearPattern",
                "name": self.name,
                "suppressed": False,
                "namespace": "",
                "parameters": [
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.FEATURE.value,
                        "parameterId": "patternType",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterFeatureList-1749",
                        "featureIds": list(self.feature_queries),
                        "parameterId": "instanceFunction",
                        "parameterName": "",
                    },
                    self._build_direction_query(),
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.distance,
                        "units": "",
                        "expression": distance_expression,
                        "parameterId": "distance",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": True,
                        "value": self.count,
                        "units": "",
                        "expression": str(self.count),
                        "parameterId": "instanceCount",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": self.reapply_features,
                        "parameterId": "fullFeaturePattern",
                        "parameterName": "",
                    },
                ],
            },
        }


class CircularPatternBuilder:
    """Builder for creating Onshape circular (feature) pattern features.

    The rotation axis needs a real line. The MCP handler creates a construction
    line through the origin (see ``axis_helper.build_axis_sketch``) and passes
    its edge's deterministic id to :meth:`build`.
    """

    def __init__(
        self,
        name: str = "Circular pattern",
        count: int = 4,
    ):
        self.name = name
        self.count = count
        self.angle = 360.0
        self.angle_variable: Optional[str] = None
        self.feature_queries: List[str] = []
        self.axis = "Z"
        self.reapply_features = False

    def set_count(self, count: int) -> "CircularPatternBuilder":
        """Set the number of pattern instances (including the original)."""
        self.count = count
        return self

    def set_angle(
        self, angle: float, variable_name: Optional[str] = None
    ) -> "CircularPatternBuilder":
        """Set the total angle spread for the pattern (degrees)."""
        self.angle = angle
        self.angle_variable = variable_name
        return self

    def add_feature(self, feature_id: str) -> "CircularPatternBuilder":
        """Add a feature to pattern by its deterministic ID."""
        self.feature_queries.append(feature_id)
        return self

    def set_reapply_features(self, reapply: bool = True) -> "CircularPatternBuilder":
        """Re-run the patterned features per instance ("Reapply features" in the UI).

        Onshape's default copies the features' resulting bodies. If those bodies were
        modified by later features (fillet, chamfer, boolean...), regeneration fails
        with PATTERN_SWITCH_TO_PER_INSTANCE; enabling this makes each instance re-execute
        the original features instead.
        """
        self.reapply_features = reapply
        return self

    def set_axis(self, axis: str) -> "CircularPatternBuilder":
        """Set the rotation axis ("X", "Y", or "Z")."""
        self.axis = normalize_axis(axis)
        return self

    def build(self, axis_edge_id: Optional[str] = None) -> Dict[str, Any]:
        """Build the circular pattern feature JSON.

        Args:
            axis_edge_id: Deterministic id of the axis line (from the helper
                construction-line sketch created by the MCP handler).

        Raises:
            ValueError: If no features were added or no axis edge was supplied
        """
        if not self.feature_queries:
            raise ValueError("At least one feature must be added")
        if not axis_edge_id:
            raise ValueError("axis_edge_id is required (create an axis construction line first)")

        angle_expression = f"#{self.angle_variable}" if self.angle_variable else f"{self.angle} deg"

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "circularPattern",
                "name": self.name,
                "suppressed": False,
                "namespace": "",
                "parameters": [
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.FEATURE.value,
                        "parameterId": "patternType",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterFeatureList-1749",
                        "featureIds": list(self.feature_queries),
                        "parameterId": "instanceFunction",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [
                            {
                                "btType": "BTMIndividualQuery-138",
                                "deterministicIds": [axis_edge_id],
                            }
                        ],
                        "parameterId": "axis",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.angle,
                        "units": "",
                        "expression": angle_expression,
                        "parameterId": "angle",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": True,
                        "value": self.count,
                        "units": "",
                        "expression": str(self.count),
                        "parameterId": "instanceCount",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": True,
                        "parameterId": "equalSpace",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": self.reapply_features,
                        "parameterId": "fullFeaturePattern",
                        "parameterName": "",
                    },
                ],
            },
        }
