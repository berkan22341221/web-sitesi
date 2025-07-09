import os
from app import app, db, User
from werkzeug.security import generate_password_hash

def reset_admin():
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
            
            # Create admin user with a secure password hash
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
            
            # Verify the admin user was created
            admin_user = User.query.filter_by(email='admin@admin.com').first()
            if admin_user:
                print("\n=== ADMIN USER CREATED SUCCESSFULLY ===")
                print(f"Email: {admin_user.email}")
                print(f"Username: {admin_user.username}")
                print(f"Is Admin: {admin_user.is_admin}")
                print("\nYou can now login with:")
                print("Email: admin@admin.com")
                print("Password: admin123")
                print("\nLogin URL: http://127.0.0.1:5000/admin/login")
            else:
                print("\nError: Failed to create admin user")
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    reset_admin()
