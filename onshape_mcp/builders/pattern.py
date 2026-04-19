"""Pattern feature builders for Onshape."""

from enum import Enum
from typing import Any, Dict, List, Optional


class PatternType(Enum):
    """Pattern entity type."""

    PART = "PART"
    FEATURE = "FEATURE"
    FACE = "FACE"


_AXIS_TO_WORLD_EDGE = {"X": "Right", "Y": "Top", "Z": "Front"}


def _axis_query_string(axis: str) -> str:
    world_edge = _AXIS_TO_WORLD_EDGE[axis]
    return f'query = qNthElement(qCreatedBy(makeId("{world_edge}"), EntityType.EDGE), 0);'


def _entities_query(feature_ids: List[str]) -> Dict[str, Any]:
    """Build an entities query selecting bodies created by the given features.

    PART-type patterns require BODY queries per source feature so downstream
    fillet/chamfer features don't break the solver.
    """
    return {
        "btType": "BTMParameterQueryList-148",
        "parameterId": "entities",
        "parameterName": "",
        "libraryRelationType": "NONE",
        "queries": [
            {
                "btType": "BTMIndividualQuery-138",
                "deterministicIds": [],
                "queryStatement": None,
                "queryString": f'query = qCreatedBy(makeId("{fid}"), EntityType.BODY);',
            }
            for fid in feature_ids
        ],
    }


class LinearPatternBuilder:
    """Builder for creating Onshape linear pattern features (PART-type)."""

    def __init__(
        self,
        name: str = "Linear pattern",
        distance: float = 1.0,
        count: int = 2,
    ):
        self.name = name
        self.distance = distance
        self.count = count
        self.distance_variable: Optional[str] = None
        self.feature_queries: List[str] = []
        self.direction_axis = "X"

    def set_distance(
        self, distance: float, variable_name: Optional[str] = None
    ) -> "LinearPatternBuilder":
        self.distance = distance
        self.distance_variable = variable_name
        return self

    def set_count(self, count: int) -> "LinearPatternBuilder":
        self.count = count
        return self

    def add_feature(self, feature_id: str) -> "LinearPatternBuilder":
        self.feature_queries.append(feature_id)
        return self

    def set_direction(self, axis: str) -> "LinearPatternBuilder":
        if axis not in _AXIS_TO_WORLD_EDGE:
            raise ValueError(f"axis must be one of {sorted(_AXIS_TO_WORLD_EDGE)}")
        self.direction_axis = axis
        return self

    def _build_direction_query(self) -> Dict[str, Any]:
        return {
            "btType": "BTMParameterQueryList-148",
            "parameterId": "directionOne",
            "parameterName": "",
            "libraryRelationType": "NONE",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [],
                    "queryStatement": None,
                    "queryString": _axis_query_string(self.direction_axis),
                }
            ],
        }

    def build(self) -> Dict[str, Any]:
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
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "PatternType",
                        "value": PatternType.PART.value,
                        "parameterId": "patternType",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    _entities_query(self.feature_queries),
                    self._build_direction_query(),
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
    """Builder for creating Onshape circular pattern features (PART-type)."""

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

    def set_count(self, count: int) -> "CircularPatternBuilder":
        self.count = count
        return self

    def set_angle(
        self, angle: float, variable_name: Optional[str] = None
    ) -> "CircularPatternBuilder":
        self.angle = angle
        self.angle_variable = variable_name
        return self

    def add_feature(self, feature_id: str) -> "CircularPatternBuilder":
        self.feature_queries.append(feature_id)
        return self

    def set_axis(self, axis: str) -> "CircularPatternBuilder":
        if axis not in _AXIS_TO_WORLD_EDGE:
            raise ValueError(f"axis must be one of {sorted(_AXIS_TO_WORLD_EDGE)}")
        self.axis = axis
        return self

    def _build_axis_query(self) -> Dict[str, Any]:
        return {
            "btType": "BTMParameterQueryList-148",
            "parameterId": "axis",
            "parameterName": "",
            "libraryRelationType": "NONE",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [],
                    "queryStatement": None,
                    "queryString": _axis_query_string(self.axis),
                }
            ],
        }

    def build(self) -> Dict[str, Any]:
        if not self.feature_queries:
            raise ValueError("At least one feature must be added")

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
                        "value": PatternType.PART.value,
                        "parameterId": "patternType",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    _entities_query(self.feature_queries),
                    self._build_axis_query(),
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
