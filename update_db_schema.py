from app import app, db

with app.app_context():
    # This will create all tables that don't exist yet
    db.create_all()
    print("Database schema updated successfully!")
