from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        # Delete any existing admin with this email
        User.query.filter_by(email='admin@admin.com').delete()
        
        # Create new admin user
        admin = User(
            username='admin',
            email='admin@admin.com',
            password=generate_password_hash('admin123', method='sha256'),
            is_admin=True,
            email_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        # Verify the user was created
        created = User.query.filter_by(email='admin@admin.com').first()
        if created:
            print("Admin user created successfully!")
            print(f"Email: {created.email}")
            print(f"Is Admin: {created.is_admin}")
        else:
            print("Failed to create admin user!")

if __name__ == '__main__':
    create_admin()
