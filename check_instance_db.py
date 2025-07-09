import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

def check_instance_db():
    db_path = os.path.join('instance', 'phone_shop.db')
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
        
    print(f"Checking database at: {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\n=== TABLES IN DATABASE ===")
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # If this is the user table, show users
            if 'user' in table_name.lower():
                try:
                    cursor.execute(f"SELECT * FROM {table_name}")
                    users = cursor.fetchall()
                    print(f"\n=== USERS IN {table_name.upper()} ===")
                    for user in users:
                        print(f"\nUser ID: {user[0]}")
                        print(f"Username: {user[1] if len(user) > 1 else 'N/A'}")
                        print(f"Email: {user[2] if len(user) > 2 else 'N/A'}")
                        if len(user) > 6:  # Check if is_admin exists in the table
                            print(f"Is Admin: {bool(user[6])}")
                except Exception as e:
                    print(f"Could not read users: {str(e)}")
    
    except Exception as e:
        print(f"Error checking database: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_instance_db()
