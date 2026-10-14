from backend.database.models import Conversation, Message


def payload(message="How do I apply?"):
    return {"message": message}


def test_valid_chat_response(client, fake_ai):
    response = client.post("/chat", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "fake answer for How do I apply?"
    assert body["language"] == "hinglish"
    assert body["sources"] == [{"document": "handbook.pdf", "page": 2, "section": "General"}]
    assert body["confidence"] == 0.91
    assert body["conversation_id"]
    assert body["response_id"] > 0
    assert fake_ai.calls[0]["history"] == []


def test_chat_validation(client):
    for message in ("", "   "):
        response = client.post("/chat", json=payload(message))
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
    response = client.post("/chat", json=payload("x" * 1001))
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    malformed = client.post("/chat", json={"message": 4})
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "VALIDATION_ERROR"


def test_ai_failures_do_not_save_turn(client, db_session, fake_ai):
    for mode, expected in (("unavailable", 503), ("timeout", 504), ("invalid", 502)):
        fake_ai.mode = mode
        response = client.post("/chat", json=payload(mode))
        assert response.status_code == expected
        assert response.json()["code"] in {"AI_UNAVAILABLE", "AI_TIMEOUT", "AI_INVALID_RESPONSE"}
        assert db_session.query(Conversation).count() == 0
        assert db_session.query(Message).count() == 0
        fake_ai.mode = "normal"


def test_follow_up_sends_previous_turn_to_ai(client, fake_ai):
    first = client.post("/chat", json=payload("first question")).json()
    second = client.post(
        "/chat", json={"conversation_id": first["conversation_id"], "message": "follow up"}
    )
    assert second.status_code == 200
    assert fake_ai.calls[1]["conversation_id"] == first["conversation_id"]
    assert fake_ai.calls[1]["history"] == [
        {"user": "first question", "assistant": "fake answer for first question"}
    ]


def test_history_is_limited_to_six_turns(client, fake_ai):
    conversation_id = None
    for index in range(8):
        body = {"message": f"question-{index}"}
        if conversation_id:
            body["conversation_id"] = conversation_id
        response = client.post("/chat", json=body)
        assert response.status_code == 200
        conversation_id = response.json()["conversation_id"]
    assert len(fake_ai.calls[-1]["history"]) == 6
    assert fake_ai.calls[-1]["history"][0]["user"] == "question-1"
    assert fake_ai.calls[-1]["history"][-1]["user"] == "question-6"


def test_anonymous_chat_works(client, fake_ai):
    response = client.post("/chat", json=payload("anonymous question"))
    assert response.status_code == 200
    assert fake_ai.calls[-1]["message"] == "anonymous question"


def test_logged_in_chat_stores_user_id(client, db_session, student_user, student_token):
    response = client.post(
        "/chat", json=payload(), headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    conversation = db_session.get(Conversation, response.json()["conversation_id"])
    assert conversation.user_id == student_user.id
