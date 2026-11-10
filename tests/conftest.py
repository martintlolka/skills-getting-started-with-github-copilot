from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture
def expected_activities():
    return deepcopy(INITIAL_ACTIVITIES)


@pytest.fixture(autouse=True)
def reset_activities(monkeypatch, expected_activities):
    monkeypatch.setattr(app_module, "activities", deepcopy(expected_activities))


@pytest.fixture
def client(reset_activities):
    with TestClient(app_module.app) as test_client:
        yield test_client
