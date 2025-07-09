from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin():
    with app.app_context():
        try:
            # Delete any existing admin with this email
            User.query.filter_by(email='admin@admin.com').delete()
            db.session.commit()
            
            # Create new admin user with minimal required fields
            admin = User(
                username='admin',
                email='admin@admin.com',
                password=generate_password_hash('admin123', method='sha256'),
                is_admin=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(admin)
            db.session.commit()
            
            # Verify the user was created
            created = User.query.filter_by(email='admin@admin.com').first()
            if created:
                print("\n=== ADMIN USER CREATED SUCCESSFULLY ===")
                print(f"Email: {created.email}")
                print(f"Is Admin: {created.is_admin}")
                print(f"ID: {created.id}")
                print("\nYou can now login with:")
                print("Email: admin@admin.com")
                print("Password: admin123")
                print("\nAccess the admin panel at: http://127.0.0.1:5000/admin/login")
            else:
                print("Failed to create admin user!")
                
        except Exception as e:
            print(f"\n=== ERROR CREATING ADMIN USER ===")
            print(f"Error: {str(e)}")
            print("\nTrying alternative method...")
            
            try:
                # Try alternative method using direct SQL
                from sqlalchemy.sql import text
                db.session.execute(text("""
                    INSERT INTO user (username, email, password, is_admin, created_at)
                    VALUES ('admin', 'admin@admin.com', :password, 1, datetime('now'))
                    ON CONFLICT(email) DO UPDATE 
                    SET password = :password, is_admin = 1
                """), {'password': generate_password_hash('admin123', method='sha256')})
                db.session.commit()
                print("\nAdmin user created/updated using direct SQL method!")
            except Exception as sql_error:
                print(f"\nSQL method also failed: {str(sql_error)}")
                db.session.rollback()

if __name__ == '__main__':
    create_admin()
