from flask import current_app
from app import db
from datetime import datetime

def upgrade():
    # Add shipping_address_id column to order table
    with current_app.app_context():
        db.session.execute('''
        ALTER TABLE "order"
        ADD COLUMN shipping_address_id INTEGER
        REFERENCES shipping_address(id)
        ''')
        db.session.commit()

def downgrade():
    # Remove shipping_address_id column from order table
    with current_app.app_context():
        db.session.execute('''
        CREATE TABLE "order_new" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            total_amount FLOAT NOT NULL,
            payment_method VARCHAR(50) NOT NULL,
            payment_status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        # Copy data from old table to new table
        db.session.execute('''
        INSERT INTO "order_new" (id, user_id, status, total_amount, payment_method, payment_status, created_at, updated_at)
        SELECT id, user_id, status, total_amount, payment_method, payment_status, created_at, updated_at
        FROM "order"
        ''')
        
        # Drop old table and rename new one
        db.session.execute('DROP TABLE "order"')
        db.session.execute('ALTER TABLE "order_new" RENAME TO "order"')
        db.session.commit()
