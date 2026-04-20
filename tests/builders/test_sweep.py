"""Unit tests for SweepBuilder."""

import pytest

from onshape_mcp.builders.sweep import SweepBuilder, SweepOperationType


class TestSweepBuilder:
    def test_requires_profile_and_path(self):
        with pytest.raises(ValueError, match="profile"):
            SweepBuilder(path_sketch_feature_id="p").build()
        with pytest.raises(ValueError, match="path"):
            SweepBuilder(profile_sketch_feature_id="x").build()

    def test_builds_minimum_shape(self):
        data = SweepBuilder(name="MySweep").set_profile("profile_sk").set_path("path_sk").build()
        feature = data["feature"]
        assert feature["featureType"] == "sweep"
        assert feature["name"] == "MySweep"

        params = {p["parameterId"]: p for p in feature["parameters"]}
        assert params["operationType"]["value"] == "NEW"
        assert params["profiles"]["queries"][0]["featureId"] == "profile_sk"
        assert "path_sk" in params["path"]["queries"][0]["queryString"]
        assert params["keepProfileOrientation"]["value"] is False

    def test_keep_orientation_and_op_type(self):
        data = SweepBuilder(
            profile_sketch_feature_id="p",
            path_sketch_feature_id="q",
            operation_type=SweepOperationType.REMOVE,
            keep_profile_orientation=True,
        ).build()
        params = {p["parameterId"]: p for p in data["feature"]["parameters"]}
        assert params["operationType"]["value"] == "REMOVE"
        assert params["keepProfileOrientation"]["value"] is True
