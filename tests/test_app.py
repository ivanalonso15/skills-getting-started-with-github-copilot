import uuid
from copy import deepcopy
import pytest

from fastapi.testclient import TestClient
from src import app as app_module

client = TestClient(app_module.app)

# Snapshot of the initial in-memory activities to restore between tests
initial_activities = deepcopy(app_module.activities)

@pytest.fixture(autouse=True)
def reset_activities():
    # Restore the activities dict to its initial state before each test
    app_module.activities.clear()
    app_module.activities.update(deepcopy(initial_activities))
    yield


def test_get_activities():
    res = client.get("/activities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data


def test_signup_and_unregister_flow():
    activity = "Chess Club"
    # generate a unique email to avoid collisions
    email = f"testuser+{uuid.uuid4().hex}@example.com"

    # Ensure email not already present
    res = client.get("/activities")
    participants_before = res.json()[activity]["participants"].copy()

    # Sign up the new email (use params so + is handled correctly)
    signup_res = client.post(f"/activities/{activity}/signup", params={"email": email})
    assert signup_res.status_code == 200
    assert email in signup_res.json().get("message", "")

    # Confirm participant was added
    res_after = client.get("/activities")
    participants_after = res_after.json()[activity]["participants"]
    assert email in participants_after
    assert len(participants_after) == len(participants_before) + 1

    # Now unregister the participant
    delete_res = client.delete(f"/activities/{activity}/participants", params={"email": email})
    assert delete_res.status_code == 200
    assert email in delete_res.json().get("message", "")

    # Confirm participant removed
    res_final = client.get("/activities")
    participants_final = res_final.json()[activity]["participants"]
    assert email not in participants_final
    assert len(participants_final) == len(participants_before)


def test_signup_duplicate():
    existing = app_module.activities["Chess Club"]["participants"][0]
    activity = "Chess Club"
    # Signup with an existing email should return 400
    res = client.post(f"/activities/{activity}/signup", params={"email": existing})
    assert res.status_code == 400
    data = res.json()
    assert "already signed up" in data.get("detail", "").lower()


def test_unregister_participant_not_found():
    activity = "Chess Club"
    res = client.delete(f"/activities/{activity}/participants", params={"email": "nonexistent@example.com"})
    assert res.status_code == 404
    data = res.json()
    assert "not" in data.get("detail", "").lower()
