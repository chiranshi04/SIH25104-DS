from backend.tests.conftest import make_user
from backend.database.models import Feedback


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_response(client, message="question", headers=None):
    return client.post("/chat", json={"message": message}, headers=headers or {}).json()


def test_positive_negative_and_update_feedback(client, student_token):
    body = make_response(client, headers=auth(student_token))
    payload = {"response_id": body["response_id"], "feedback": "positive"}
    first = client.post("/feedback", json=payload, headers=auth(student_token))
    assert first.status_code == 200
    changed = client.post(
        "/feedback",
        json={**payload, "feedback": "negative", "conversation_id": body["conversation_id"]},
        headers=auth(student_token),
    )
    assert changed.status_code == 200
    assert changed.json()["feedback"] == "negative"
    assert client.post("/feedback", json=payload, headers=auth(student_token)).status_code == 200
    assert client.post("/feedback", json=payload, headers=auth(student_token)).json()["feedback"] == "positive"


def test_feedback_validation_and_missing_response(client, student_token):
    missing = client.post(
        "/feedback", json={"response_id": 99999, "feedback": "positive"}, headers=auth(student_token)
    )
    assert missing.status_code == 404
    invalid = client.post(
        "/feedback", json={"response_id": 1, "feedback": "meh"}, headers=auth(student_token)
    )
    assert invalid.status_code == 422


def test_feedback_cannot_be_given_on_another_users_response(client, db_session, student_user, student_token):
    other = make_user(db_session, "Other", "other@example.com", "student")
    other_token = __import__("backend.auth.security", fromlist=["create_access_token"]).create_access_token(other.id, other.role)
    response = make_response(client, headers=auth(student_token))
    forbidden = client.post(
        "/feedback",
        json={"response_id": response["response_id"], "feedback": "positive"},
        headers=auth(other_token),
    )
    assert forbidden.status_code == 403


def test_anonymous_feedback_and_admin_reporting(client, admin_token, staff_token):
    body = make_response(client, message="anonymous question")
    saved = client.post(
        "/feedback",
        json={"response_id": body["response_id"], "feedback": "positive"},
    )
    assert saved.status_code == 200
    page = client.get("/admin/feedback", headers=auth(admin_token))
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["question"] == "anonymous question"
    assert page.json()["items"][0]["feedback"] == "positive"
    filtered = client.get("/admin/feedback?feedback=negative", headers=auth(staff_token))
    assert filtered.json()["total"] == 0
    stats = client.get("/admin/stats", headers=auth(admin_token))
    assert stats.status_code == 200
    assert stats.json()["feedback_positive"] == 1
    assert stats.json()["feedback_negative"] == 0
