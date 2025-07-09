from app import app, db, User
from werkzeug.security import generate_password_hash

def verify_admin():
    with app.app_context():
        try:
            # Check if admin user exists
            admin = User.query.filter_by(email='admin@admin.com').first()
            
            if admin:
                print("\n=== ADMIN USER FOUND ===")
                print(f"Email: {admin.email}")
                print(f"Is Admin: {admin.is_admin}")
                print(f"Password Hash: {admin.password}")
                
                # Update admin user to ensure it has admin privileges
                admin.is_admin = True
                admin.password = generate_password_hash('admin123', method='sha256')
                db.session.commit()
                print("\nAdmin user verified and updated.")
            else:
                # Create admin user if it doesn't exist
                admin = User(
                    username='admin',
                    email='admin@admin.com',
                    password=generate_password_hash('admin123', method='sha256'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("\n=== NEW ADMIN USER CREATED ===")
                print("Email: admin@admin.com")
                print("Password: admin123")
            
            print("\nYou can now login at: http://127.0.0.1:5000/admin/login")
            print("Use the following credentials:")
            print("Email: admin@admin.com")
            print("Password: admin123")
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Make sure the database is properly initialized.")
            print("Try running 'python -c \"from app import app, db; app.app_context().push(); db.create_all()\"'")

if __name__ == '__main__':
    verify_admin()
