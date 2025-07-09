from app import app, db, User
from werkzeug.security import generate_password_hash

def setup():
    with app.app_context():
        # Veritabanını oluştur
        db.create_all()
        
        # Admin kullanıcısını oluştur
        admin = User(
            username='admin',
            email='admin@admin.com',
            password=generate_password_hash('admin123', method='sha256'),
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("\n✅ Veritabanı ve admin kullanıcısı oluşturuldu!")
        print("-" * 50)
        print("E-posta: admin@admin.com")
        print("Şifre: admin123")
        print("-" * 50)
        print("\nUygulamayı başlatmak için 'python app.py' komutunu çalıştırın.")

if __name__ == '__main__':
    setup()
