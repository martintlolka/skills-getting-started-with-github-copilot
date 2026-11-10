from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep

import pytest

from src import app as app_module


class SlowMembershipList(list):
    def __contains__(self, value):
        result = super().__contains__(value)
        # Widen the race window between checking membership and mutating the list.
        sleep(0.05)
        return result


def test_root_redirects_to_static_page(client):
    expected_location = "/static/index.html"

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_static_page_is_served(client):
    expected_title = "<title>Mergington High School Activities</title>"

    response = client.get("/static/index.html")

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == "text/html"
    assert expected_title in response.text


def test_get_activities_returns_all_details(client, expected_activities):
    expected_response = expected_activities

    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == expected_response


def test_signup_adds_one_participant(client, expected_activities):
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    expected_activities[activity_name]["participants"].append(email)
    expected_message = f"Signed up {email} for {activity_name}"

    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    activities_response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == {"message": expected_message}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


@pytest.mark.parametrize(
    "method, activity_name, email, expected_status, expected_detail",
    [
        pytest.param(
            "POST", "Chess Club", "michael@mergington.edu", 409,
            "Student is already signed up", id="duplicate-signup",
        ),
        pytest.param(
            "POST", "Unknown Club", "new.student@mergington.edu", 404,
            "Activity not found", id="signup-unknown-activity",
        ),
        pytest.param(
            "DELETE", "Unknown Club", "new.student@mergington.edu", 404,
            "Activity not found", id="unregister-unknown-activity",
        ),
        pytest.param(
            "DELETE", "Chess Club", "new.student@mergington.edu", 404,
            "Student is not signed up", id="unregister-nonparticipant",
        ),
    ],
)
def test_rejected_signup_changes_nothing(
    client, expected_activities, method, activity_name, email,
    expected_status, expected_detail,
):
    endpoint = f"/activities/{activity_name}/signup"
    expected_response = {"detail": expected_detail}

    response = client.request(method, endpoint, params={"email": email})
    activities_response = client.get("/activities")

    assert response.status_code == expected_status
    assert response.json() == expected_response
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_signup_requires_email(client, expected_activities, method):
    endpoint = "/activities/Chess Club/signup"
    expected_error_location = ["query", "email"]

    response = client.request(method, endpoint)
    activities_response = client.get("/activities")

    assert response.status_code == 422
    assert any(
        error["loc"] == expected_error_location
        and error["type"] in ("missing", "value_error.missing")
        for error in response.json()["detail"]
    )
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


def test_unregister_removes_participant(client, expected_activities):
    activity_name = "Chess Club"
    email = "michael@mergington.edu"
    expected_activities[activity_name]["participants"].remove(email)
    expected_message = f"Unregistered {email} from {activity_name}"

    response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    activities_response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == {"message": expected_message}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


def test_student_can_sign_up_again_after_unregistering(client, expected_activities):
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    endpoint = f"/activities/{activity_name}/signup"
    params = {"email": email}
    expected_signup = {"message": f"Signed up {email} for {activity_name}"}
    expected_unregister = {"message": f"Unregistered {email} from {activity_name}"}
    expected_activities[activity_name]["participants"].append(email)

    signup_response = client.post(endpoint, params=params)
    unregister_response = client.delete(endpoint, params=params)
    second_signup_response = client.post(endpoint, params=params)
    activities_response = client.get("/activities")

    assert signup_response.status_code == 200
    assert signup_response.json() == expected_signup
    assert unregister_response.status_code == 200
    assert unregister_response.json() == expected_unregister
    assert second_signup_response.status_code == 200
    assert second_signup_response.json() == expected_signup
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


@pytest.mark.parametrize(
    "method, expected_statuses, expected_detail",
    [
        ("POST", [200, 409], "Student is already signed up"),
        ("DELETE", [200, 404], "Student is not signed up"),
    ],
)
def test_concurrent_requests_change_participant_once(
    client, expected_activities, method, expected_statuses, expected_detail,
):
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    participants = SlowMembershipList(
        expected_activities[activity_name]["participants"]
    )
    if method == "DELETE":
        participants.append(email)
    else:
        expected_activities[activity_name]["participants"].append(email)
    app_module.activities[activity_name]["participants"] = participants
    start = Barrier(2)
    expected_message = (
        f"Signed up {email} for {activity_name}" if method == "POST"
        else f"Unregistered {email} from {activity_name}"
    )

    def send_request():
        start.wait(timeout=5)
        return client.request(
            method, f"/activities/{activity_name}/signup", params={"email": email}
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(send_request) for _ in range(2)]
        responses = [future.result(timeout=10) for future in futures]
    activities_response = client.get("/activities")

    assert sorted(response.status_code for response in responses) == expected_statuses
    assert [response.json() for response in responses if response.status_code == 200] == [
        {"message": expected_message}
    ]
    assert [
        response.json() for response in responses if response.status_code != 200
    ] == [{"detail": expected_detail}]
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities
