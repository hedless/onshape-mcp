"""Pattern feature builders for Onshape."""

from enum import Enum
from typing import Any, Dict, List, Optional


class PatternType(Enum):
    """Pattern entity type."""

    PART = "PART"
    FEATURE = "FEATURE"
    FACE = "FACE"


class LinearPatternBuilder:
    """Builder for creating Onshape linear pattern features."""

    def __init__(
        self,
        name: str = "Linear pattern",
        distance: float = 1.0,
        count: int = 2,
    ):
        """Initialize linear pattern builder.

        Args:
            name: Name of the pattern feature
            distance: Spacing between instances in inches
            count: Total number of instances including the original
        """
        self.name = name
        self.distance = distance
        self.count = count
        self.distance_variable: Optional[str] = None
        self.feature_queries: List[str] = []
        self.direction_entity_id: Optional[str] = None

    def set_distance(
        self, distance: float, variable_name: Optional[str] = None
    ) -> "LinearPatternBuilder":
        """Set the distance between pattern instances.

        Args:
            distance: Distance in inches
            variable_name: Optional variable name to reference

        Returns:
            Self for chaining
        """
        self.distance = distance
        self.distance_variable = variable_name
        return self

    def set_count(self, count: int) -> "LinearPatternBuilder":
        """Set the number of pattern instances.

        Args:
            count: Total number of instances including the original

        Returns:
            Self for chaining
        """
        self.count = count
        return self

    def add_feature(self, feature_id: str) -> "LinearPatternBuilder":
        """Add a feature to pattern by its deterministic ID.

        Args:
            feature_id: Deterministic ID of the feature to pattern

        Returns:
            Self for chaining
        """
        self.feature_queries.append(feature_id)
        return self

    def set_direction_entity(self, entity_id: str) -> "LinearPatternBuilder":
        """Set the edge (or linear/cylindrical face) that defines the pattern direction.

        Onshape has no always-present "X/Y/Z axis" entity to select by default --
        the direction must be a real edge or face's deterministic ID. Use
        get_body_details or an eval_featurescript query (e.g. qCreatedBy(makeId(
        "<featureId>"), EntityType.EDGE) via evaluateQuery) to resolve one.

        Args:
            entity_id: Deterministic ID of the edge/face defining the direction

        Returns:
            Self for chaining
        """
        self.direction_entity_id = entity_id
        return self

    def _build_direction_query(self) -> Dict[str, Any]:
        """Build the direction axis query parameter.

        Returns:
            Direction query parameter dictionary
        """
        return {
            "btType": "BTMParameterQueryList-148",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [self.direction_entity_id],
                }
            ],
            "parameterId": "directionQuery",
        }

    def build(self) -> Dict[str, Any]:
        """Build the linear pattern feature JSON.

        Returns:
            Feature definition for Onshape API

        Raises:
            ValueError: If no features have been added
        """
        if not self.feature_queries:
            raise ValueError("At least one feature must be added")
        if not self.direction_entity_id:
            raise ValueError(
                "Direction entity must be set via set_direction_entity() before building. "
                "Onshape has no default axis entity -- resolve a real edge/face ID first."
            )

        distance_expression = (
            f"#{self.distance_variable}" if self.distance_variable else f"{self.distance} in"
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
                        "btType": "BTMParameterQueryList-148",
                        "queries": [
                            {
                                "btType": "BTMIndividualQuery-138",
                                "deterministicIds": self.feature_queries,
                            }
                        ],
                        "parameterId": "entities",
                    },
                    self._build_direction_query(),
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.FEATURE.value,
                        "parameterId": "patternType",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.distance,
                        "units": "",
                        "expression": distance_expression,
                        "parameterId": "distance",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": True,
                        "value": self.count,
                        "units": "",
                        "expression": str(self.count),
                        "parameterId": "instanceCount",
                    },
                ],
            },
        }


class CircularPatternBuilder:
    """Builder for creating Onshape circular pattern features."""

    def __init__(
        self,
        name: str = "Circular pattern",
        count: int = 4,
    ):
        """Initialize circular pattern builder.

        Args:
            name: Name of the pattern feature
            count: Total number of instances including the original
        """
        self.name = name
        self.count = count
        self.angle = 360.0
        self.angle_variable: Optional[str] = None
        self.feature_queries: List[str] = []
        self.axis_entity_id: Optional[str] = None

    def set_count(self, count: int) -> "CircularPatternBuilder":
        """Set the number of pattern instances.

        Args:
            count: Total number of instances including the original

        Returns:
            Self for chaining
        """
        self.count = count
        return self

    def set_angle(self, angle: float, variable_name: Optional[str] = None) -> "CircularPatternBuilder":
        """Set the total angle spread for the pattern.

        Args:
            angle: Total angle in degrees
            variable_name: Optional variable name to reference

        Returns:
            Self for chaining
        """
        self.angle = angle
        self.angle_variable = variable_name
        return self

    def add_feature(self, feature_id: str) -> "CircularPatternBuilder":
        """Add a feature to pattern by its deterministic ID.

        Args:
            feature_id: Deterministic ID of the feature to pattern

        Returns:
            Self for chaining
        """
        self.feature_queries.append(feature_id)
        return self

    def set_axis_entity(self, entity_id: str) -> "CircularPatternBuilder":
        """Set the edge or cylindrical/conical face that defines the rotation axis.

        Onshape has no always-present "X/Y/Z axis" entity to select by default --
        the axis must be a real edge or face's deterministic ID (e.g. a circular
        edge, or a cylindrical face whose implicit axis is used). Use
        get_body_details or an eval_featurescript query (e.g. qCreatedBy(makeId(
        "<featureId>"), EntityType.EDGE) via evaluateQuery) to resolve one.

        Args:
            entity_id: Deterministic ID of the edge/face defining the axis

        Returns:
            Self for chaining
        """
        self.axis_entity_id = entity_id
        return self

    def _build_axis_query(self) -> Dict[str, Any]:
        """Build the rotation axis query parameter.

        Returns:
            Axis query parameter dictionary
        """
        return {
            "btType": "BTMParameterQueryList-148",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [self.axis_entity_id],
                }
            ],
            "parameterId": "axisQuery",
        }

    def build(self) -> Dict[str, Any]:
        """Build the circular pattern feature JSON.

        Returns:
            Feature definition for Onshape API

        Raises:
            ValueError: If no features have been added
        """
        if not self.feature_queries:
            raise ValueError("At least one feature must be added")
        if not self.axis_entity_id:
            raise ValueError(
                "Axis entity must be set via set_axis_entity() before building. "
                "Onshape has no default axis entity -- resolve a real edge/face ID first."
            )

        angle_expression = (
            f"#{self.angle_variable}" if self.angle_variable else f"{self.angle} deg"
        )

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
                        "btType": "BTMParameterQueryList-148",
                        "queries": [
                            {
                                "btType": "BTMIndividualQuery-138",
                                "deterministicIds": self.feature_queries,
                            }
                        ],
                        "parameterId": "entities",
                    },
                    self._build_axis_query(),
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.FEATURE.value,
                        "parameterId": "patternType",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.angle,
                        "units": "",
                        "expression": angle_expression,
                        "parameterId": "angle",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": True,
                        "value": self.count,
                        "units": "",
                        "expression": str(self.count),
                        "parameterId": "instanceCount",
                    },
                ],
            },
        }
