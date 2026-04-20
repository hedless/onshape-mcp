"""Loft feature builder for Onshape."""

from enum import Enum
from typing import Any, Dict, List


class LoftOperationType(Enum):
    """Loft operation type."""

    NEW = "NEW"
    ADD = "ADD"
    REMOVE = "REMOVE"
    INTERSECT = "INTERSECT"


class LoftBuilder:
    """Builder for creating Onshape loft features between two or more sketch profiles."""

    def __init__(
        self,
        name: str = "Loft",
        operation_type: LoftOperationType = LoftOperationType.NEW,
    ):
        self.name = name
        self.operation_type = operation_type
        self._profile_sketch_ids: List[str] = []
        self.closed: bool = False

    def add_profile(self, sketch_feature_id: str) -> "LoftBuilder":
        """Add a sketch profile. The order determines the loft direction."""
        self._profile_sketch_ids.append(sketch_feature_id)
        return self

    def set_closed(self, closed: bool = True) -> "LoftBuilder":
        """Close the loft (last profile loops back to the first)."""
        self.closed = closed
        return self

    @staticmethod
    def _profile_item(sketch_feature_id: str) -> Dict[str, Any]:
        return {
            "btType": "BTMArrayParameterItem-1843",
            "parameters": [
                {
                    "btType": "BTMParameterQueryList-148",
                    "parameterId": "profileSubquery",
                    "parameterName": "",
                    "libraryRelationType": "NONE",
                    "queries": [
                        {
                            "btType": "BTMIndividualSketchRegionQuery-140",
                            "featureId": sketch_feature_id,
                            "filterInnerLoops": False,
                            "queryStatement": None,
                            "queryString": (
                                f'query = qSketchRegion(id + "{sketch_feature_id}", false);'
                            ),
                            "deterministicIds": [],
                        }
                    ],
                }
            ],
        }

    def build(self) -> Dict[str, Any]:
        if len(self._profile_sketch_ids) < 2:
            raise ValueError("Loft requires at least two profiles")

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "loft",
                "name": self.name,
                "suppressed": False,
                "namespace": "",
                "parameters": [
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "NewBodyOperationType",
                        "value": self.operation_type.value,
                        "parameterId": "operationType",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    {
                        "btType": "BTMParameterArray-2025",
                        "parameterId": "profileSubqueries",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                        "items": [self._profile_item(sid) for sid in self._profile_sketch_ids],
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": False,
                        "parameterId": "addGuides",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": self.closed,
                        "parameterId": "makePeriodic",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                ],
            },
        }
