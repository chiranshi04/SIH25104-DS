"""
create_admin.py
---------------
.env se admin user create karne ka idempotent script.
"""

from sqlalchemy import select

from backend.auth.security import hash_password
from backend.config import settings
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User


def main() -> None:
    required = {
        "ADMIN_NAME": settings.ADMIN_NAME,
        "ADMIN_EMAIL": settings.ADMIN_EMAIL,
        "ADMIN_PASSWORD": settings.ADMIN_PASSWORD,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(", ".join(missing) + " must be set in .env")
    if len(settings.ADMIN_PASSWORD) < 8:
        raise SystemExit("ADMIN_PASSWORD must be at least 8 characters")

    init_db()
    db = SessionLocal()
    try:
        email = settings.ADMIN_EMAIL.lower()
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            db.add(
                User(
                    name=settings.ADMIN_NAME,
                    email=email,
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                )
            )
            db.commit()
            print(f"Created admin user: {email}")
        else:
            print(f"Admin user already exists: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
