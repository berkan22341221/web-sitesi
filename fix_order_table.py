from app import app, db

def fix_order_table():
    with app.app_context():
        try:
            print("Starting database fix...")
            
            # Begin transaction
            db.session.begin()
            
            # 1. Rename existing order table to order_old
            print("Renaming existing order table...")
            db.session.execute('ALTER TABLE "order" RENAME TO order_old')
            
            # 2. Create new order table with correct schema
            print("Creating new order table...")
            db.session.execute('''
            CREATE TABLE "order" (
                id INTEGER NOT NULL, 
                user_id INTEGER NOT NULL, 
                status VARCHAR(20), 
                total_amount FLOAT, 
                payment_method VARCHAR(50), 
                payment_status VARCHAR(20), 
                created_at DATETIME, 
                updated_at DATETIME, 
                shipping_address_id INTEGER, 
                PRIMARY KEY (id), 
                FOREIGN KEY(user_id) REFERENCES user (id), 
                FOREIGN KEY(shipping_address_id) REFERENCES shipping_address (id)
            )
            ''')
            
            # 3. Copy data from old table to new table
            print("Copying data to new table...")
            db.session.execute('''
            INSERT INTO "order" (
                id, user_id, status, total_amount, 
                payment_method, payment_status, created_at, updated_at
            )
            SELECT 
                id, user_id, status, total_amount, 
                payment_method, payment_status, created_at, updated_at
            FROM order_old
            ''')
            
            # 4. Drop the old table
            print("Cleaning up old table...")
            db.session.execute('DROP TABLE order_old')
            
            # Commit the transaction
            db.session.commit()
            print("Database updated successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            raise

if __name__ == '__main__':
    fix_order_table()
