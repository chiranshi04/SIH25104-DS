def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_conversation_list_and_history_restore(client, student_token, fake_ai):
    first = client.post("/chat", json={"message": "first"}, headers=auth(student_token)).json()
    second = client.post(
        "/chat",
        json={"conversation_id": first["conversation_id"], "message": "second"},
        headers=auth(student_token),
    ).json()
    listing = client.get("/conversations", headers=auth(student_token))
    assert listing.status_code == 200
    assert listing.json()["conversations"][0]["id"] == first["conversation_id"]
    assert listing.json()["conversations"][0]["preview"] == "first"
    history = client.get(f"/conversations/{first['conversation_id']}", headers=auth(student_token))
    assert history.status_code == 200
    assert [item["sender"] for item in history.json()["messages"]] == ["user", "assistant", "user", "assistant"]
    assert history.json()["messages"][1]["language"] == "hinglish"
    assert history.json()["messages"][1]["sources"][0]["document"] == "handbook.pdf"
    assert history.json()["messages"][1]["response_id"] == first["response_id"]
    assert second["response_id"] != first["response_id"]


def test_conversation_access_and_missing(client, student_token, staff_token, fake_ai):
    body = client.post("/chat", json={"message": "private"}, headers=auth(student_token)).json()
    assert client.get(f"/conversations/{body['conversation_id']}").status_code == 403
    assert client.get(f"/conversations/{body['conversation_id']}", headers=auth(staff_token)).status_code == 403
    assert client.get("/conversations/99999999-9999-4999-8999-999999999999").status_code == 404
    assert client.get("/conversations", headers=auth(student_token)).status_code == 200


def test_invalid_conversation_id(client, fake_ai):
    response = client.post("/chat", json={"conversation_id": "not-a-uuid", "message": "hi"})
    assert response.status_code == 422
