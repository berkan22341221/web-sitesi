from app import app, db, User
from werkzeug.security import generate_password_hash

def fix_admin_user():
    with app.app_context():
        try:
            # Find or create admin user
            admin = User.query.filter_by(email='admin@admin.com').first()
            
            if not admin:
                # Create new admin user if doesn't exist
                admin = User(
                    username='admin',
                    email='admin@admin.com',
                    password=generate_password_hash('admin123', method='sha256'),
                    is_admin=True
                )
                db.session.add(admin)
                print("Created new admin user")
            else:
                # Update existing user to be admin
                admin.is_admin = True
                admin.password = generate_password_hash('admin123', method='sha256')
                print("Updated existing admin user")
            
            db.session.commit()
            print("\n=== ADMIN USER READY ===")
            print("Email: admin@admin.com")
            print("Password: admin123")
            print("\nYou can now login at: http://127.0.0.1:5000/admin/login")
            
        except Exception as e:
            print(f"Error fixing admin user: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    fix_admin_user()
