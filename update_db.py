from app import app, db
from migrations.add_shipping_address_to_order import upgrade

def update_database():
    with app.app_context():
        print("Updating database...")
        upgrade()
        print("Database update completed successfully!")

if __name__ == '__main__':
    update_database()
