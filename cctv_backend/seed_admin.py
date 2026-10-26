"""
One-time bootstrap: creates the very first admin account directly in the
DB (bypassing the API, since /auth/users requires an existing admin
token to call). Run this once after setting up the database.

Usage:
    python seed_admin.py <username> <password> [email]
"""
import sys

from app.database import SessionLocal, Base, engine
from app.models import User, UserRole
from app.security import hash_password


def main():
    if len(sys.argv) < 3:
        print("Usage: python seed_admin.py <username> <password> [email]")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"User '{username}' already exists.")
            return

        admin = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.admin,
        )
        db.add(admin)
        db.commit()
        print(f"Admin user '{username}' created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
