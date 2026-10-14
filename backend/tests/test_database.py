from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from backend.database.models import (
    Conversation,
    Document,
    Feedback,
    Message,
    Notice,
    Response,
    Source,
    User,
)


def test_create_read_update_delete_all_models(db_session):
    user = User(name="User", email="db@example.com", password_hash="hash", role="student")
    db_session.add(user)
    db_session.commit()
    conversation = Conversation(id="11111111-1111-4111-8111-111111111111", user_id=user.id)
    db_session.add(conversation)
    db_session.flush()
    user_message = Message(conversation_id=conversation.id, sender="user", message="question")
    assistant_message = Message(conversation_id=conversation.id, sender="assistant", message="answer")
    db_session.add_all([user_message, assistant_message])
    db_session.flush()
    response = Response(
        message_id=assistant_message.id,
        answer="answer",
        language="english",
        confidence=0.9,
    )
    db_session.add(response)
    db_session.flush()
    source = Source(response_id=response.id, document="guide.pdf", page=1, section="Intro")
    feedback = Feedback(response_id=response.id, feedback="positive")
    notice = Notice(title="Notice", content="Content", created_by=user.id)
    document = Document(
        original_filename="guide.txt",
        stored_filename="stored.txt",
        content_type="text/plain",
        size_bytes=7,
        sha256="a" * 64,
        uploaded_by=user.id,
    )
    db_session.add_all([source, feedback, notice, document])
    db_session.commit()
    assert db_session.get(User, user.id).email == "db@example.com"
    assert db_session.get(Conversation, conversation.id).messages
    assert db_session.get(Response, response.id).sources[0].document == "guide.pdf"
    assert db_session.get(Notice, notice.id).content == "Content"
    assert db_session.get(Document, document.id).size_bytes == 7
    notice.content = "Updated"
    db_session.commit()
    assert db_session.get(Notice, notice.id).content == "Updated"
    db_session.delete(document)
    db_session.delete(notice)
    db_session.delete(user)
    db_session.commit()
    assert db_session.get(User, user.id) is None
    assert db_session.get(Document, document.id) is None
    assert db_session.get(Notice, notice.id) is None


def test_conversation_cascade_deletes_related_rows(db_session):
    conversation = Conversation(id="22222222-2222-4222-8222-222222222222")
    db_session.add(conversation)
    db_session.flush()
    user_message = Message(conversation_id=conversation.id, sender="user", message="q")
    assistant = Message(conversation_id=conversation.id, sender="assistant", message="a")
    db_session.add_all([user_message, assistant])
    db_session.flush()
    response = Response(message_id=assistant.id, answer="a", language="en", confidence=0.5)
    db_session.add(response)
    db_session.flush()
    db_session.add_all([
        Source(response_id=response.id, document="x", page=None, section=None),
        Feedback(response_id=response.id, feedback="negative"),
    ])
    db_session.commit()
    db_session.delete(conversation)
    db_session.commit()
    assert db_session.query(Message).count() == 0
    assert db_session.query(Response).count() == 0
    assert db_session.query(Source).count() == 0
    assert db_session.query(Feedback).count() == 0


def test_unique_constraints(db_session):
    db_session.add_all([
        User(name="A", email="same@example.com", password_hash="x"),
        User(name="B", email="same@example.com", password_hash="y"),
    ])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    conversation = Conversation(id="33333333-3333-4333-8333-333333333333")
    message = Message(conversation_id=conversation.id, sender="assistant", message="a")
    db_session.add_all([conversation, message])
    db_session.flush()
    response = Response(message_id=message.id, answer="a", language="en", confidence=0.5)
    db_session.add(response)
    db_session.flush()
    db_session.add_all([
        Feedback(response_id=response.id, feedback="positive"),
        Feedback(response_id=response.id, feedback="negative"),
    ])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_check_constraints(db_session):
    conversation = Conversation(id="44444444-4444-4444-8444-444444444444")
    db_session.add(conversation)
    db_session.commit()
    db_session.add(Message(conversation_id=conversation.id, sender="system", message="bad"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    message = Message(conversation_id=conversation.id, sender="assistant", message="a")
    db_session.add(message)
    db_session.flush()
    response = Response(message_id=message.id, answer="a", language="en", confidence=0.1)
    db_session.add(response)
    db_session.flush()
    db_session.add(Feedback(response_id=response.id, feedback="meh"))
    with pytest.raises(IntegrityError):
        db_session.commit()
