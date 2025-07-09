import sqlite3
from werkzeug.security import check_password_hash

def check_users():
    # Connect to the database
    conn = sqlite3.connect('phone_shop.db')
    cursor = conn.cursor()
    
    try:
        # Get all users
        cursor.execute("SELECT id, username, email, password, is_admin FROM user")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database!")
            return
            
        print("\n=== USERS IN DATABASE ===")
        for user in users:
            user_id, username, email, password_hash, is_admin = user
            print(f"\nID: {user_id}")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Is Admin: {bool(is_admin)}")
            
            # Try to check password
            try:
                if check_password_hash(password_hash, 'admin123'):
                    print("✅ Password 'admin123' is CORRECT for this user")
                else:
                    print("❌ Password 'admin123' is INCORRECT for this user")
            except Exception as e:
                print(f"⚠️ Could not verify password: {str(e)}")
                print(f"Password hash: {password_hash}")
    
    except Exception as e:
        print(f"Error checking database: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_users()
