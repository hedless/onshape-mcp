"""Sweep feature builder for Onshape."""

from enum import Enum
from typing import Any, Dict, Optional


class SweepOperationType(Enum):
    """Sweep operation type."""

    NEW = "NEW"
    ADD = "ADD"
    REMOVE = "REMOVE"
    INTERSECT = "INTERSECT"


class SweepBuilder:
    """Builder for creating Onshape sweep features (profile along a path)."""

    def __init__(
        self,
        name: str = "Sweep",
        profile_sketch_feature_id: Optional[str] = None,
        path_sketch_feature_id: Optional[str] = None,
        operation_type: SweepOperationType = SweepOperationType.NEW,
        keep_profile_orientation: bool = False,
    ):
        self.name = name
        self.profile_sketch_feature_id = profile_sketch_feature_id
        self.path_sketch_feature_id = path_sketch_feature_id
        self.operation_type = operation_type
        self.keep_profile_orientation = keep_profile_orientation

    def set_profile(self, sketch_feature_id: str) -> "SweepBuilder":
        self.profile_sketch_feature_id = sketch_feature_id
        return self

    def set_path(self, sketch_feature_id: str) -> "SweepBuilder":
        self.path_sketch_feature_id = sketch_feature_id
        return self

    def build(self) -> Dict[str, Any]:
        if not self.profile_sketch_feature_id:
            raise ValueError("Sweep profile sketch must be set before building")
        if not self.path_sketch_feature_id:
            raise ValueError("Sweep path sketch must be set before building")

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "sweep",
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
                        "btType": "BTMParameterQueryList-148",
                        "parameterId": "profiles",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                        "queries": [
                            {
                                "btType": "BTMIndividualSketchRegionQuery-140",
                                "featureId": self.profile_sketch_feature_id,
                                "filterInnerLoops": False,
                                "queryStatement": None,
                                "queryString": (
                                    f'query = qSketchRegion(id + "{self.profile_sketch_feature_id}"'
                                    ", false);"
                                ),
                                "deterministicIds": [],
                            }
                        ],
                    },
                    {
                        "btType": "BTMParameterQueryList-148",
                        "parameterId": "path",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                        "queries": [
                            {
                                "btType": "BTMIndividualQuery-138",
                                "queryStatement": None,
                                "deterministicIds": [],
                                "queryString": (
                                    f'query = qCreatedBy(makeId("{self.path_sketch_feature_id}")'
                                    ", EntityType.EDGE);"
                                ),
                            }
                        ],
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": self.keep_profile_orientation,
                        "parameterId": "keepProfileOrientation",
                        "parameterName": "",
                        "libraryRelationType": "NONE",
                    },
                ],
            },
        }
