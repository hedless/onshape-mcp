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
        self.direction_axis = "X"

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

    def set_direction(self, axis: str) -> "LinearPatternBuilder":
        """Set the pattern direction axis.

        Args:
            axis: Direction axis ("X", "Y", or "Z")

        Returns:
            Self for chaining
        """
        self.direction_axis = axis
        return self

    def _build_direction_query(self) -> Dict[str, Any]:
        """Build the direction axis query parameter.

        Default Part Studio planes have no edges, so the prior
        ``qCreatedBy(makeId("FRONT"), EntityType.EDGE)`` query returned an
        empty selection. We pick the axis of any cylindrical face in the
        Part Studio; Onshape uses that cylinder's axis as the direction.
        Caller must ensure a cylindrical body aligned with the desired
        direction already exists.

        Returns:
            Direction query parameter dictionary
        """
        return {
            "btType": "BTMParameterQueryList-148",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [],
                    "queryStatement": None,
                    "queryString": (
                        "query = qNthElement(qGeometry(qOwnedByBody("
                        "qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), "
                        "EntityType.FACE), GeometryType.CYLINDER), 0);"
                    ),
                }
            ],
            "parameterId": "directionQuery",
            "parameterName": "",
            "libraryRelationType": "NONE",
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
                                "deterministicIds": [],
                                "queryStatement": None,
                                "queryString": (
                                    "query = qUnion(["
                                    + ", ".join(
                                        f'qCreatedBy(makeId("{fid}"))'
                                        for fid in self.feature_queries
                                    )
                                    + "]);"
                                ),
                            }
                        ],
                        "parameterId": "entities",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    self._build_direction_query(),
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.FEATURE.value,
                        "parameterId": "patternType",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.distance,
                        "units": "",
                        "expression": distance_expression,
                        "parameterId": "distance",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": True,
                        "value": self.count,
                        "units": "",
                        "expression": str(self.count),
                        "parameterId": "instanceCount",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
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
        self.axis = "Z"

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

    def set_axis(self, axis: str) -> "CircularPatternBuilder":
        """Set the pattern rotation axis.

        Args:
            axis: Rotation axis ("X", "Y", or "Z")

        Returns:
            Self for chaining
        """
        self.axis = axis
        return self

    def _build_axis_query(self) -> Dict[str, Any]:
        """Build the rotation axis query parameter.

        Onshape default Part Studios do not expose origin axes as queryable
        line entities; the prior approach of querying default-plane edges
        returns empty. We pick the axis of any cylindrical face in the Part
        Studio. For circular patterns of cuts/features around a coaxial body
        (the common case), this resolves to the body's symmetry axis.

        Returns:
            Axis query parameter dictionary
        """
        return {
            "btType": "BTMParameterQueryList-148",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [],
                    "queryStatement": None,
                    "queryString": (
                        "query = qNthElement(qGeometry(qOwnedByBody("
                        "qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), "
                        "EntityType.FACE), GeometryType.CYLINDER), 0);"
                    ),
                }
            ],
            "parameterId": "axisQuery",
            "parameterName": "",
            "libraryRelationType": "NONE",
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
                                "deterministicIds": [],
                                "queryStatement": None,
                                "queryString": (
                                    "query = qUnion(["
                                    + ", ".join(
                                        f'qCreatedBy(makeId("{fid}"))'
                                        for fid in self.feature_queries
                                    )
                                    + "]);"
                                ),
                            }
                        ],
                        "parameterId": "entities",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    self._build_axis_query(),
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.FEATURE.value,
                        "parameterId": "patternType",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.angle,
                        "units": "",
                        "expression": angle_expression,
                        "parameterId": "angle",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": True,
                        "value": self.count,
                        "units": "",
                        "expression": str(self.count),
                        "parameterId": "instanceCount",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                ],
            },
        }
