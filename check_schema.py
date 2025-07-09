import sqlite3

def check_schema():
    # Connect to the database
    conn = sqlite3.connect('phone_shop.db')
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
    
    except Exception as e:
        print(f"Error checking schema: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_schema()
