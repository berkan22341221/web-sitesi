from app import app, db
import os

def fix_database():
    with app.app_context():
        # Check if the shipping_address_id column exists in the order table
        result = db.session.execute("""
            PRAGMA table_info([order])
        """)
        columns = [row[1] for row in result]
        
        if 'shipping_address_id' not in columns:
            print("Adding shipping_address_id column to order table...")
            try:
                # Create a new table with the correct schema
                db.session.execute('''
                CREATE TABLE order_new (
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
                
                # Copy data from old table to new table
                db.session.execute('''
                INSERT INTO order_new (id, user_id, status, total_amount, 
                                     payment_method, payment_status, created_at, updated_at)
                SELECT id, user_id, status, total_amount, 
                       payment_method, payment_status, created_at, updated_at
                FROM "order"
                ''')
                
                # Drop old table and rename new one
                db.session.execute('DROP TABLE "order"')
                db.session.execute('ALTER TABLE order_new RENAME TO "order"')
                
                db.session.commit()
                print("Database updated successfully!")
                
            except Exception as e:
                db.session.rollback()
                print(f"Error updating database: {str(e)}")
                raise
        else:
            print("shipping_address_id column already exists in order table.")

if __name__ == '__main__':
    fix_database()
