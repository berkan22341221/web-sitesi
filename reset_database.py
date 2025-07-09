import os
from app import app, db

def reset_database():
    with app.app_context():
        # Tüm tabloları sil
        db.drop_all()
        print("Tüm tablolar silindi.")
        
        # Yeni tabloları oluştur
        db.create_all()
        print("Yeni tablolar oluşturuldu.")
        
        # Veritabanı dosyasını kontrol et
        db_path = os.path.join(os.path.dirname(__file__), 'instance', 'site.db')
        if os.path.exists(db_path):
            print(f"Veritabanı dosyası bulundu: {db_path}")
        else:
            print("Uyarı: Veritabanı dosyası oluşturulamadı!")

if __name__ == '__main__':
    reset_database()
