from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin_user():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@admin.com').first()
        if admin:
            print("Admin user already exists!")
            print(f"Email: {admin.email}")
            print(f"Is Admin: {admin.is_admin}")
            return
        
        # Create new admin user
        admin = User(
            username='admin',
            email='admin@admin.com',
            password=generate_password_hash('admin123', method='sha256'),
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
        print(f"Email: admin@admin.com")
        print("Password: admin123")

if __name__ == '__main__':
    create_admin_user()
