import os
from app import app, db

def init_database():
    with app.app_context():
        # Delete the existing database file if it exists
        db_file = 'phone_shop.db'
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"Removed existing database file: {db_file}")
            except Exception as e:
                print(f"Error removing database file: {e}")
                return
        
        # Create all database tables
        try:
            db.create_all()
            print("Successfully created all database tables!")
            print("Database initialization complete.")
        except Exception as e:
            print(f"Error creating database tables: {e}")

if __name__ == '__main__':
    print("Initializing database...")
    init_database()
