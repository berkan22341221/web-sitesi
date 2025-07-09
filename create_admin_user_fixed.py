from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin():
    with app.app_context():
        # Delete any existing admin with this email
        User.query.filter_by(email='admin@admin.com').delete()
        
        try:
            # Create new admin user with all required fields
            admin = User(
                username='admin',
                email='admin@admin.com',
                password=generate_password_hash('admin123', method='sha256'),
                is_admin=True,
                created_at=datetime.utcnow(),
                email_verified=True,
                phone_verified=False  # Add this field if it exists in your model
            )
            
            db.session.add(admin)
            db.session.commit()
            
            # Verify the user was created
            created = User.query.filter_by(email='admin@admin.com').first()
            if created:
                print("Admin user created successfully!")
                print(f"Email: {created.email}")
                print(f"Is Admin: {created.is_admin}")
                print(f"ID: {created.id}")
            else:
                print("Failed to create admin user!")
                
        except Exception as e:
            print(f"Error creating admin user: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    create_admin()
