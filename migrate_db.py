from app import app, db
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

def run_migrations():
    # Configure the application for migrations
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///phone_shop.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # This will create the migrations folder if it doesn't exist
    # and generate a new migration
    print("Running database migrations...")
    
    # You'll need to run these commands manually:
    print("Please run the following commands in your terminal:")
    print("1. flask db init  # Only if this is the first time setting up migrations")
    print("2. flask db migrate -m 'Add shipping_address_id to order table'")
    print("3. flask db upgrade")
    print("\nNote: Make sure to activate your virtual environment first.")

if __name__ == '__main__':
    run_migrations()
