from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@admin.com').first()
        if admin:
            print(f"Admin user exists! ID: {admin.id}, Email: {admin.email}, Is Admin: {admin.is_admin}")
            print(f"Password hash: {admin.password}")
        else:
            print("No admin user found with email 'admin@admin.com'")
            
        # List all admin users
        print("\nAll admin users:")
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            print(f"ID: {admin.id}, Email: {admin.email}, Is Admin: {admin.is_admin}")

if __name__ == '__main__':
    create_admin()
