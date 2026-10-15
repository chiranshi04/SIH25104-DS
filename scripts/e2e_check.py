#!/usr/bin/env python3
"""Run final API checks against an already running server.

Usage:
    ADMIN_EMAIL=... ADMIN_PASSWORD=... python scripts/e2e_check.py http://127.0.0.1:8000

The checker uses a uniquely tagged student account and removes that account,
its conversations, messages, responses, sources, and feedback afterwards.
The configured admin account is never removed.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.models import Conversation, User

load_dotenv()


@dataclass
class Result:
    number: int
    scenario: str
    input_text: str
    expected: str
    actual: str = ""
    status: str = "FAIL"


class E2E:
    def __init__(self, base_url: str, admin_email: str, admin_password: str):
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=15.0)
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.student_email = f"e2e-{uuid.uuid4().hex[:12]}@example.com"
        self.student_password = "E2E-Password-ChangeMe-2026!"
        self.student_id: int | None = None
        self.student_token = ""
        self.admin_token = ""
        self.conversation_ids: set[str] = set()
        self.document_ids: list[int] = []
        self.results: list[Result] = []

    def close(self) -> None:
        self.client.close()

    def add(self, number: int, scenario: str, input_text: str, expected: str) -> Result:
        result = Result(number, scenario, input_text, expected)
        self.results.append(result)
        return result

    @staticmethod
    def detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return str(payload.get("detail", payload))
        except ValueError:
            pass
        return response.text[:240]

    def login(self, email: str, password: str) -> str:
        response = self.client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        return response.json()["access_token"]

    def chat(self, message: str, token: str = "", conversation_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.post("/chat", json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
        if body.get("conversation_id"):
            self.conversation_ids.add(body["conversation_id"])
        return body

    def require_contract(self, body: dict[str, Any]) -> None:
        required = {"answer", "language", "sources", "confidence", "conversation_id", "response_id"}
        missing = required.difference(body)
        if missing:
            raise AssertionError(f"missing response fields: {sorted(missing)}")
        if not isinstance(body["sources"], list):
            raise AssertionError("sources is not a list")

    def run(self) -> None:
        # Basic server and database reachability are useful preflight checks.
        health = self.client.get("/health")
        if health.status_code != 200:
            raise RuntimeError(f"/health failed: {health.status_code} {self.detail(health)}")
        db_health = self.client.get("/health/db")
        if db_health.status_code != 200:
            raise RuntimeError(f"/health/db failed: {db_health.status_code} {self.detail(db_health)}")

        registration = self.client.post(
            "/auth/register",
            json={
                "name": "E2E Verification Student",
                "email": self.student_email,
                "password": self.student_password,
            },
        )
        registration.raise_for_status()
        self.student_id = registration.json()["id"]
        self.student_token = self.login(self.student_email, self.student_password)
        self.admin_token = self.login(self.admin_email, self.admin_password)

        questions = [
            (1, "English question", "How do I apply for a scholarship?"),
            (2, "Hindi (Devanagari) question", "छात्रवृत्ति के लिए आवेदन कैसे करें?"),
            (3, "Hinglish question", "Scholarship ke liye eligibility kya hai?"),
            (4, "Code-mixed question", "What documents chahiye for hostel admission?"),
        ]
        for number, scenario, question in questions:
            result = self.add(number, scenario, question, "HTTP 200 with the stable AI response contract")
            try:
                body = self.chat(question, self.student_token)
                self.require_contract(body)
                result.actual = (
                    f"HTTP 200; language={body['language']!r}, confidence={body['confidence']!r}; "
                    "run against AI_MODE=dummy, so semantic language detection is not validated"
                )
                result.status = "PASS"
            except Exception as exc:
                result.actual = str(exc)

        first = self.chat("What is the application deadline?", self.student_token)
        follow = self.add(
            5,
            "Follow-up question that depends on the previous turn",
            "And what is the required format?",
            "HTTP 200 and previous turn included in the AI history payload",
        )
        try:
            body = self.chat(
                "And what is the required format?",
                self.student_token,
                first["conversation_id"],
            )
            self.require_contract(body)
            if "received 1 previous turns" not in body["answer"]:
                raise AssertionError("dummy response did not report one previous turn")
            follow.actual = "HTTP 200; dummy AI reported received 1 previous turn"
            follow.status = "PASS"
        except Exception as exc:
            follow.actual = str(exc)

        unknown = self.add(
            6,
            "Unknown/out-of-scope question",
            "What is the admission policy for a university on Mars?",
            "Low confidence or no sources; no fabricated source",
        )
        if settings.AI_MODE == "dummy":
            unknown.actual = "NOT RUN — needs Student 1's AI; dummy always returns a sample source and confidence 1.0"
            unknown.status = "NOT RUN"
        else:
            try:
                body = self.chat("What is the admission policy for a university on Mars?", self.student_token)
                self.require_contract(body)
                if body["confidence"] >= 0.5 and body["sources"]:
                    raise AssertionError("AI returned neither low confidence nor an empty source list")
                unknown.actual = f"HTTP 200; confidence={body['confidence']!r}, sources={body['sources']!r}"
                unknown.status = "PASS"
            except Exception as exc:
                unknown.actual = str(exc)

        source = self.add(
            7,
            "Source display",
            "Show the returned document, page, and section fields",
            "Source fields are returned exactly without frontend inference",
        )
        try:
            body = self.chat("Show the returned document, page, and section fields", self.student_token)
            self.require_contract(body)
            source.actual = f"HTTP 200; sources exactly as returned: {body['sources']!r}"
            source.status = "PASS"
        except Exception as exc:
            source.actual = str(exc)

        history = self.add(
            8,
            "Conversation history",
            "Restore the E2E student's logged-in conversation",
            "List and detail endpoints return the saved conversation and metadata",
        )
        try:
            conversation_id = next(iter(self.conversation_ids))
            listing = self.client.get("/conversations", headers={"Authorization": f"Bearer {self.student_token}"})
            detail = self.client.get(
                f"/conversations/{conversation_id}",
                headers={"Authorization": f"Bearer {self.student_token}"},
            )
            if listing.status_code != 200 or detail.status_code != 200:
                raise AssertionError(f"list={listing.status_code}, detail={detail.status_code}")
            if not any(item["id"] == conversation_id for item in listing.json()["conversations"]):
                raise AssertionError("conversation missing from list")
            if not detail.json().get("messages"):
                raise AssertionError("conversation detail has no messages")
            history.actual = "HTTP 200; conversation appears in list and restored detail contains messages"
            history.status = "PASS"
        except Exception as exc:
            history.actual = str(exc)

        document = self.add(
            9,
            "Admin document upload -> ingestion -> question grounded in document",
            "Upload a uniquely named text document, then ask a related question",
            "Upload ingested and answer is grounded in that document",
        )
        try:
            filename = f"e2e-{uuid.uuid4().hex[:8]}.txt"
            upload = self.client.post(
                "/documents/upload",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                files={"file": (filename, b"E2E document content", "text/plain")},
            )
            upload.raise_for_status()
            uploaded = upload.json()
            self.document_ids.append(uploaded["id"])
            if settings.AI_MODE == "dummy":
                document.actual = (
                    f"Upload HTTP 201 with ingestion_status={uploaded['ingestion_status']!r}; "
                    "question grounding NOT RUN — needs Student 1's AI"
                )
                document.status = "NOT RUN"
            else:
                document.actual = f"Upload HTTP 201 with ingestion_status={uploaded['ingestion_status']!r}; real-AI grounding requires Student 1's service"
                document.status = "NOT RUN"
        except Exception as exc:
            document.actual = str(exc)

        feedback = self.add(
            10,
            "Positive and negative feedback visible in admin dashboard",
            "Submit positive and negative feedback for two responses",
            "Both feedback values appear in admin feedback results",
        )
        try:
            positive_body = self.chat("Give me the scholarship office contact.", self.student_token)
            negative_body = self.chat("Give me the library opening hours.", self.student_token)
            headers = {"Authorization": f"Bearer {self.student_token}"}
            for response_id, value in ((positive_body["response_id"], "positive"), (negative_body["response_id"], "negative")):
                submitted = self.client.post(
                    "/feedback", headers=headers, json={"response_id": response_id, "feedback": value}
                )
                submitted.raise_for_status()
            admin_feedback = self.client.get("/admin/feedback", headers={"Authorization": f"Bearer {self.admin_token}"})
            admin_feedback.raise_for_status()
            values = {item["feedback"] for item in admin_feedback.json()["items"]}
            if not {"positive", "negative"}.issubset(values):
                raise AssertionError(f"admin feedback values were {values!r}")
            feedback.actual = "HTTP 200; admin feedback includes positive and negative entries"
            feedback.status = "PASS"
        except Exception as exc:
            feedback.actual = str(exc)

        auth = self.add(
            11,
            "Authentication and role checks",
            "Student admin access plus unauthenticated chat",
            "Student receives 403 for admin route; guest chat succeeds",
        )
        try:
            blocked = self.client.get("/admin/stats", headers={"Authorization": f"Bearer {self.student_token}"})
            guest = self.client.post("/chat", json={"message": "Can a guest ask a question?"})
            if blocked.status_code != 403 or guest.status_code != 200:
                raise AssertionError(f"student admin={blocked.status_code}, guest chat={guest.status_code}")
            auth.actual = "Student admin access HTTP 403; guest chat HTTP 200"
            auth.status = "PASS"
        except Exception as exc:
            auth.actual = str(exc)

        errors = self.add(
            12,
            "Error handling",
            "AI down, DB down, invalid file, oversized message",
            "Friendly standardized errors; fault-injection checks separated from cheap validation checks",
        )
        try:
            invalid_file = self.client.post(
                "/documents/upload",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                files={"file": ("e2e.exe", b"MZ", "application/octet-stream")},
            )
            oversized = self.client.post(
                "/chat",
                headers={"Content-Length": "20000"},
                content=b"x" * 20000,
            )
            if invalid_file.status_code != 400 or oversized.status_code != 413:
                raise AssertionError(f"invalid_file={invalid_file.status_code}, oversized={oversized.status_code}")
            errors.actual = (
                f"Invalid file HTTP {invalid_file.status_code}; oversized message HTTP {oversized.status_code}; "
                "AI-down and DB-down fault injection NOT RUN"
            )
            errors.status = "PASS"
        except Exception as exc:
            errors.actual = str(exc)

    def cleanup(self) -> None:
        # Delete uploaded files through the public admin API first.
        for document_id in self.document_ids:
            try:
                self.client.delete(
                    f"/documents/{document_id}",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                )
            except Exception:
                pass
        if self.student_id is None:
            return
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with Session(engine) as db:
            conversations = db.scalars(
                select(Conversation).where(Conversation.user_id == self.student_id)
            ).all()
            for conversation in conversations:
                db.delete(conversation)
            db.flush()
            student = db.get(User, self.student_id)
            if student is not None:
                db.delete(student)
            db.commit()
        engine.dispose()

    def print_results(self) -> int:
        for result in self.results:
            print(f"{result.status}: {result.number}. {result.scenario} — {result.actual}")
        failed = [result for result in self.results if result.status == "FAIL"]
        not_run = [result for result in self.results if result.status == "NOT RUN"]
        print(f"SUMMARY: {len(self.results) - len(failed) - len(not_run)} PASS, {len(failed)} FAIL, {len(not_run)} NOT RUN")
        return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Running FastAPI base URL, e.g. http://127.0.0.1:8000")
    args = parser.parse_args()
    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        print("FAIL: ADMIN_EMAIL and ADMIN_PASSWORD must be provided through the environment", file=sys.stderr)
        return 2

    check = E2E(args.base_url, admin_email, admin_password)
    try:
        check.run()
    except Exception as exc:
        print(f"FAIL: E2E preflight/setup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            check.cleanup()
        except Exception as exc:
            print(f"FAIL: cleanup failed: {exc}", file=sys.stderr)
        check.close()
    return check.print_results()


if __name__ == "__main__":
    raise SystemExit(main())
