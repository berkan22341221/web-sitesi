from app import app, db, User
from werkzeug.security import check_password_hash

def verify_admin():
    with app.app_context():
        # Check if admin user exists
        admin = User.query.filter_by(email='admin@admin.com').first()
        
        if not admin:
            print("No admin user found with email 'admin@admin.com'")
            return
            
        print(f"Admin user found!")
        print(f"ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Is Admin: {admin.is_admin}")
        
        # Verify password
        password_correct = check_password_hash(admin.password, 'admin123')
        print(f"Password check for 'admin123': {'✓' if password_correct else '✗'}")
        
        if not admin.is_admin:
            print("WARNING: User exists but is not an admin!")
            print("Fixing admin status...")
            admin.is_admin = True
            db.session.commit()
            print("Admin status updated!")

if __name__ == '__main__':
    verify_admin()
