from app import app, db, User
from werkzeug.security import generate_password_hash

def create_new_admin():
    with app.app_context():
        # Mevcut admin kullanıcılarını temizle
        User.query.filter_by(is_admin=True).delete()
        db.session.commit()
        
        # Yeni admin kullanıcısı oluştur
        admin = User(
            username='yeniadmin',
            email='admin@admin.com',
            password=generate_password_hash('Admin123!', method='sha256'),
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("\n✅ Yeni admin kullanıcısı oluşturuldu!")
        print("-" * 50)
        print(f"E-posta: admin@admin.com")
        print(f"Şifre: Admin123!")
        print("-" * 50)
        print("\nBu bilgileri güvenli bir yere kaydedin!")

if __name__ == '__main__':
    create_new_admin()
