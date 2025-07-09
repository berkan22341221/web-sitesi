import os
from app import app, db

def recreate_database():
    with app.app_context():
        # Drop all tables
        print("Dropping all tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating all tables...")
        db.create_all()
        
        print("Database recreated successfully!")

if __name__ == '__main__':
    # Delete the existing database file if it exists
    db_path = os.path.join(os.path.dirname(__file__), 'phone_shop.db')
    if os.path.exists(db_path):
        print(f"Removing existing database file: {db_path}")
        os.remove(db_path)
    
    # Recreate the database
    recreate_database()
