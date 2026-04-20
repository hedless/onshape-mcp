"""Unit tests for LoftBuilder."""

import pytest

from onshape_mcp.builders.loft import LoftBuilder, LoftOperationType


class TestLoftBuilder:
    def test_requires_two_profiles(self):
        loft = LoftBuilder().add_profile("s1")
        with pytest.raises(ValueError, match="at least two"):
            loft.build()

    def test_builds_minimum_shape(self):
        data = LoftBuilder(name="MyLoft").add_profile("sketch_a").add_profile("sketch_b").build()
        feature = data["feature"]
        assert feature["featureType"] == "loft"
        assert feature["name"] == "MyLoft"

        params = {p["parameterId"]: p for p in feature["parameters"]}
        assert params["operationType"]["value"] == "NEW"

        profiles = params["profileSubqueries"]["items"]
        assert len(profiles) == 2
        assert profiles[0]["parameters"][0]["queries"][0]["featureId"] == "sketch_a"
        assert profiles[1]["parameters"][0]["queries"][0]["featureId"] == "sketch_b"

    def test_closed_flag_flows_through(self):
        data = LoftBuilder().add_profile("a").add_profile("b").set_closed(True).build()
        params = {p["parameterId"]: p for p in data["feature"]["parameters"]}
        assert params["makePeriodic"]["value"] is True

    def test_operation_type_flows_through(self):
        data = (
            LoftBuilder(operation_type=LoftOperationType.ADD)
            .add_profile("a")
            .add_profile("b")
            .build()
        )
        params = {p["parameterId"]: p for p in data["feature"]["parameters"]}
        assert params["operationType"]["value"] == "ADD"
