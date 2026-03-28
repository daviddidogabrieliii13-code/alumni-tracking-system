import os
import sqlite3
from models import db, User, UserRole
from app import app

with app.app_context():
    # Delete existing DB to start fresh
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Deleted {db_path}")

    # Create fresh DB
    db.create_all()
    print("Fresh DB created")

    # Seed users
    from app import seed_users
    seed_users()
    print("Users seeded")

print("Run: python app.py")
