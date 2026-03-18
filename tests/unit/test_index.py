from unittest.mock import patch, MagicMock
import pytest
import sys
import os

# Make sure the lambda folder is on the path when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

import index


def _make_ssm_mock(env_value: str) -> MagicMock:
    """Return a mock boto3 SSM client that returns the given env value."""
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {
        "Parameter": {"Value": env_value}
    }
    return mock_client


# ------------------------------------------------------------------
# Happy-path tests — one per valid environment
# ------------------------------------------------------------------

def test_development_returns_replica_count_1():
    with patch("boto3.client", return_value=_make_ssm_mock("development")):
        result = index.handler({"RequestType": "Create"}, {})
    assert result["Data"]["replicaCount"] == "1"


def test_staging_returns_replica_count_2():
    with patch("boto3.client", return_value=_make_ssm_mock("staging")):
        result = index.handler({"RequestType": "Create"}, {})
    assert result["Data"]["replicaCount"] == "2"


def test_production_returns_replica_count_2():
    with patch("boto3.client", return_value=_make_ssm_mock("production")):
        result = index.handler({"RequestType": "Create"}, {})
    assert result["Data"]["replicaCount"] == "2"


# ------------------------------------------------------------------
# Edge-case tests
# ------------------------------------------------------------------

def test_unknown_env_defaults_to_replica_count_1():
    """An unrecognised environment value should safely default to 1."""
    with patch("boto3.client", return_value=_make_ssm_mock("unknown")):
        result = index.handler({"RequestType": "Create"}, {})
    assert result["Data"]["replicaCount"] == "1"


def test_delete_event_does_not_call_ssm():
    """On Delete the handler must return without touching SSM."""
    with patch("boto3.client") as mock_boto:
        result = index.handler({"RequestType": "Delete"}, {})
    mock_boto.assert_not_called()
    assert result["PhysicalResourceId"] == "helm-values-custom-resource"


# ------------------------------------------------------------------
# Response contract tests — CloudFormation requires these fields
# ------------------------------------------------------------------

def test_response_contains_physical_resource_id():
    with patch("boto3.client", return_value=_make_ssm_mock("development")):
        result = index.handler({"RequestType": "Create"}, {})
    assert "PhysicalResourceId" in result


def test_response_contains_data_key():
    with patch("boto3.client", return_value=_make_ssm_mock("development")):
        result = index.handler({"RequestType": "Create"}, {})
    assert "Data" in result


def test_replica_count_is_string():
    """CloudFormation Custom Resource attributes must be strings."""
    with patch("boto3.client", return_value=_make_ssm_mock("production")):
        result = index.handler({"RequestType": "Update"}, {})
    assert isinstance(result["Data"]["replicaCount"], str)
