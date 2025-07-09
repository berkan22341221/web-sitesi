import os
from app import app, db, User
from werkzeug.security import generate_password_hash, check_password_hash

def setup_admin():
    with app.app_context():
        try:
            # Delete the existing database file if it exists
            db_file = 'phone_shop.db'
            if os.path.exists(db_file):
                os.remove(db_file)
                print(f"Removed existing database: {db_file}")
            
            # Create all database tables
            print("Creating database tables...")
            db.create_all()
            
            # Create admin user with more secure hashing method
            password = 'admin123'
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            
            admin = User(
                username='admin',
                email='admin@admin.com',
                password=hashed_password,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            
            # Verify the password can be checked
            test_user = User.query.filter_by(email='admin@admin.com').first()
            password_matches = check_password_hash(test_user.password, password)
            
            print("\n=== ADMIN USER CREATED ===")
            print(f"Email: {test_user.email}")
            print(f"Username: {test_user.username}")
            print(f"Is Admin: {test_user.is_admin}")
            print(f"Password matches: {password_matches}")
            print("\nYou can now login at: http://127.0.0.1:5000/admin/login")
            print("Use these credentials:")
            print("Email: admin@admin.com")
            print("Password: admin123")
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Make sure the application is not running when running this script.")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    setup_admin()
