def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_notices_crud_and_public_visibility(client, admin_token, student_token):
    create = client.post(
        "/notices",
        json={"title": "Exam schedule", "content": "The schedule is published", "is_active": True},
        headers=auth(admin_token),
    )
    assert create.status_code == 201
    notice_id = create.json()["id"]
    public = client.get("/notices")
    assert public.status_code == 200
    assert public.json()[0]["title"] == "Exam schedule"
    update = client.put(
        f"/notices/{notice_id}",
        json={"title": "Updated schedule", "is_active": False},
        headers=auth(admin_token),
    )
    assert update.status_code == 200
    assert client.get("/notices").json() == []
    assert client.get("/admin/notices", headers=auth(admin_token)).json()[0]["is_active"] is False
    assert client.delete(f"/notices/{notice_id}", headers=auth(admin_token)).status_code == 204
    assert client.put("/notices/9999", json={"title": "x"}, headers=auth(admin_token)).status_code == 404


def test_staff_can_manage_notices_but_student_cannot(client, staff_token, student_token):
    staff = client.post(
        "/notices", json={"title": "Staff notice", "content": "Content"}, headers=auth(staff_token)
    )
    assert staff.status_code == 201
    assert client.get("/admin/notices", headers=auth(staff_token)).status_code == 200
    assert client.post(
        "/notices", json={"title": "No", "content": "No"}, headers=auth(student_token)
    ).status_code == 403


def test_users_management_and_admin_cannot_deactivate_self(client, db_session, admin_user, admin_token, staff_token):
    users = client.get("/admin/users", headers=auth(staff_token))
    assert users.status_code == 200
    assert all("password_hash" not in item for item in users.json())
    self_deactivate = client.patch(
        f"/admin/users/{admin_user.id}", json={"is_active": False}, headers=auth(admin_token)
    )
    assert self_deactivate.status_code == 400
    self_demote = client.patch(
        f"/admin/users/{admin_user.id}", json={"role": "student"}, headers=auth(admin_token)
    )
    assert self_demote.status_code == 400
    target = next(item for item in users.json() if item["role"] == "staff")
    patched = client.patch(
        f"/admin/users/{target['id']}",
        json={"role": "student", "is_active": False},
        headers=auth(admin_token),
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "student"
    assert patched.json()["is_active"] is False
    assert client.patch(
        f"/admin/users/{target['id']}", json={"role": "admin"}, headers=auth(staff_token)
    ).status_code == 403
