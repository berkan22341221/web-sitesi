from app import app, db, User
from werkzeug.security import generate_password_hash

def ensure_admin():
    with app.app_context():
        try:
            # Check if admin user exists
            admin = User.query.filter_by(email='admin@admin.com').first()
            
            if admin:
                print("\n=== UPDATING EXISTING ADMIN USER ===")
                admin.username = 'admin'
                admin.password = generate_password_hash('admin123', method='pbkdf2:sha256')
                admin.is_admin = True
                db.session.commit()
                print("Admin user updated successfully!")
            else:
                print("\n=== CREATING NEW ADMIN USER ===")
                admin = User(
                    username='admin',
                    email='admin@admin.com',
                    password=generate_password_hash('admin123', method='pbkdf2:sha256'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
            
            # Verify the admin user
            admin = User.query.filter_by(email='admin@admin.com').first()
            print("\n=== ADMIN USER DETAILS ===")
            print(f"Email: {admin.email}")
            print(f"Username: {admin.username}")
            print(f"Is Admin: {admin.is_admin}")
            print("\nYou can now login with:")
            print("Email: admin@admin.com")
            print("Password: admin123")
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Make sure the database is properly initialized.")

if __name__ == '__main__':
    ensure_admin()
