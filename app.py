import os
import time
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify, session, json, Response
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text, func
from wtforms import validators

# Make Pillow optional
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    print("Warning: Pillow is not installed. Some image processing features may be limited.")
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, BaseView, expose, form, AdminIndexView
from flask_admin.menu import MenuLink
from flask_admin.model import typefmt
from datetime import datetime
from wtforms import FileField as BaseFileField
import os
import io
import base64
import secrets
import string

# Initialize Flask app
app = Flask(__name__)

def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    
    # If it's already a datetime object, use it directly
    if hasattr(value, 'strftime'):
        return value.strftime(format)
        
    # If it's a string, try to parse it
    if isinstance(value, str):
        try:
            # Try ISO format first
            if 'T' in value or ' ' in value:
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime(format)
                except (ValueError, AttributeError):
                    pass
            
            # Try other common formats if ISO format fails
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime(format)
                except (ValueError, AttributeError):
                    continue
            
            # If we get here, we couldn't parse the date
            return value
        except Exception as e:
            print(f"Error formatting date: {str(e)}")
            return value
    
    # If it's some other type, try to convert to string
    try:
        return str(value)
    except Exception as e:
        print(f"Error converting value to string: {str(e)}")
        return ''

app.jinja_env.filters['datetimeformat'] = datetimeformat

app.config['SECRET_KEY'] = 'your-secret-key-here'  # In production, use a strong, unique key
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = 'a-different-secret-key'  # Different from SECRET_KEY

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'phone_shop.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # For debugging SQL queries
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Initialize the database
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'login'
    
    # Ensure necessary directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join('static', 'images'), exist_ok=True)
    
    return app

# Create the app instance
app = create_app()

# Make CSRF token available in all templates
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def cart_count(self):
        return sum(item.quantity for item in self.cart_items)

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_path = db.Column(db.String(200), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'phone' or 'accessory'
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan')
    
    # Technical Specifications
    brand = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    color = db.Column(db.String(30), nullable=True)
    os = db.Column(db.String(50), nullable=True)
    storage = db.Column(db.String(30), nullable=True)
    ram = db.Column(db.String(30), nullable=True)
    specifications = db.Column(db.Text, nullable=True)  # Will store JSON string of specifications
    
    # Discount fields
    discounted_price = db.Column(db.Float, nullable=True, server_default='0.0')
    is_discounted = db.Column(db.Boolean, default=False, server_default='0')
    
    @property
    def primary_image(self):
        primary = next((img for img in self.images if img.is_primary), None)
        if primary:
            return primary.image_path
        return self.images[0].image_path if self.images else 'images/placeholder.png'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('shipping_address.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    address_info = db.Column(db.Text, nullable=True)  # Store address info as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='orders')
    shipping_address = db.relationship('ShippingAddress', foreign_keys=[shipping_address_id])
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Order, self).__init__(**kwargs)
        if self.shipping_address_id is None:
            self.shipping_address_id = None
    
    @property
    def total_price(self):
        """Calculate the total price of all items in the order"""
        try:
            # If total_amount is already set and order hasn't been modified, use it
            if self.total_amount and not any(item.is_dirty() for item in self.items):
                return self.total_amount
                
            # Otherwise calculate the total from order items
            total = sum(item.subtotal for item in self.items)
            # Update the total_amount if it's different
            if total != self.total_amount:
                self.total_amount = total
                db.session.commit()
            return total
        except Exception as e:
            print(f"Error calculating order total: {str(e)}")
            return self.total_amount or 0.0

class ShippingAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='shipping_addresses')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    
    product = db.relationship('Product', lazy='joined')
    
    @property
    def subtotal(self):
        """Calculate the subtotal for this order item (price * quantity)"""
        if hasattr(self, 'unit_price') and hasattr(self, 'quantity'):
            return float(getattr(self, 'unit_price', 0)) * int(getattr(self, 'quantity', 0))
        return 0.0

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    product = db.relationship('Product', backref='cart_items')
    user = db.relationship('User', backref='cart_items')

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure one favorite per user per product
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),)
    
    # Relationships
    product = db.relationship('Product', backref='favorited_by')
    user = db.relationship('User', backref='favorites')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='comments')
    product = db.relationship('Product', backref='comments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.username,
            'rating': self.rating,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M'),
            'updated_at': self.updated_at.strftime('%d.%m.%Y %H:%M') if self.updated_at else None
        }

# Admin Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("\n=== ADMIN REQUIRED DECORATOR ===")
        print(f"Current user: {current_user}")
        
        if not current_user.is_authenticated:
            print("User not authenticated, redirecting to admin login")
            return redirect(url_for('admin_login', next=request.url))
            
        print(f"User is authenticated: {current_user.id} - {current_user.email}")
        print(f"Is admin: {current_user.is_admin}")
        
        if not current_user.is_admin:
            print("User is not an admin, access denied")
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('index'))
            
        print("Admin access granted")
        return f(*args, **kwargs)
    return decorated_function

# Admin Views
class AdminModelView(ModelView):
    def is_accessible(self):
        print("\n=== ADMIN MODEL VIEW ACCESS CHECK ===")
        is_accessible = current_user.is_authenticated and current_user.is_admin
        print(f"Current user: {current_user}")
        print(f"Is authenticated: {current_user.is_authenticated}")
        print(f"Is admin: {getattr(current_user, 'is_admin', False)}")
        print(f"Access {'granted' if is_accessible else 'denied'}")
        return is_accessible
    
    def inaccessible_callback(self, name, **kwargs):
        print(f"\n=== ADMIN MODEL VIEW INACCESSIBLE CALLBACK ===")
        print(f"Current user: {current_user}")
        print(f"Requested view: {name}")
        if not current_user.is_authenticated:
            print("User not authenticated, redirecting to login")
            return redirect(url_for('admin_login', next=request.url))
        else:
            print("User authenticated but not an admin, redirecting to index")
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('index'))

# Custom admin index view with access control
class CustomAdminIndexView(AdminIndexView):
    def is_accessible(self):
        print("\n=== CUSTOM ADMIN INDEX VIEW ACCESS CHECK ===")
        is_accessible = current_user.is_authenticated and current_user.is_admin
        print(f"Current user: {current_user}")
        print(f"Is authenticated: {current_user.is_authenticated}")
        print(f"Is admin: {getattr(current_user, 'is_admin', False)}")
        print(f"Access {'granted' if is_accessible else 'denied'}")
        return is_accessible
        
    def inaccessible_callback(self, name, **kwargs):
        print("\n=== CUSTOM ADMIN INDEX VIEW INACCESSIBLE ===")
        print(f"Current user: {current_user}")
        if not current_user.is_authenticated:
            print("User not authenticated, redirecting to login")
            return redirect(url_for('admin_login', next=request.url))
        else:
            print("User authenticated but not an admin, showing access denied")
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('index'))

# Custom file upload field that doesn't use Pillow
class SimpleFileField(form.FileUploadField):
    def __init__(self, *args, **kwargs):
        self.relative_path = kwargs.pop('relative_path', 'uploads/')
        super(SimpleFileField, self).__init__(*args, **kwargs)

    def _save_file(self, data, filename):
        # Import os at the top level of the file is already done
        upload_dir = os.path.join(app.root_path, 'static', self.relative_path)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
        
        # Generate a unique filename
        filename = secure_filename(f"{int(time.time())}_{filename}")
        filepath = os.path.join(upload_dir, filename)
        
        try:
            # Save the file
            data.save(filepath)
            # Return the relative path with forward slashes for web
            return os.path.join(self.relative_path, filename).replace('\\', '/')
        except Exception as e:
            app.logger.error(f"Error saving file {filename}: {str(e)}")
            return None

class CustomModelView(AdminModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    # Disable image preview in list view to avoid Pillow dependency
    column_formatters = {
        'image_path': lambda v, c, m, p: m.image_path.split('/')[-1] if m.image_path else ''
    }
    form_overrides = {
        'image_path': SimpleFileField
    }
    form_args = {
        'image_path': {
            'base_path': os.path.join(app.root_path, 'static/uploads'),
            'relative_path': 'uploads/'
        },
        'discounted_price': {
            'validators': [validators.Optional()]
        }
    }
    form_widget_args = {
        'discounted_price': {
            'placeholder': 'Leave empty if no discount',
            'step': '0.01',
            'min': '0.01'
        },
        'price': {
            'step': '0.01',
            'min': '0.01'
        }
    }
    form_excluded_columns = ['images']
    
    def on_model_change(self, form, model, is_created):
        # Automatically set is_discounted based on whether discounted_price is set
        if model.discounted_price is not None and model.discounted_price > 0:
            model.is_discounted = True
        else:
            model.is_discounted = False
            model.discounted_price = None

# Initialize Flask-Admin with our custom views
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4', index_view=CustomAdminIndexView())
admin.add_view(CustomModelView(User, db.session, 'Kullanıcılar'))
admin.add_view(CustomModelView(Product, db.session, 'Ürünler'))
# We're using a custom view for orders, so we don't add it to the admin panel
admin.add_view(CustomModelView(CartItem, db.session, 'Sepet Öğeleri'))
admin.add_view(CustomModelView(Favorite, db.session, 'Favoriler'))

@login_manager.user_loader
def load_user(user_id):
    # Use db.session.get() for better session management
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        print(f"Error loading user {user_id}: {str(e)}")
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def save_uploaded_file(file):
    if not file or file.filename == '':
        app.logger.warning("No file provided or empty filename")
        return None
    
    try:
        # Ensure the file has an allowed extension
        if not allowed_file(file.filename):
            app.logger.error(f"File type not allowed: {file.filename}")
            return None
            
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(app.root_path, 'static', 'uploads')
        try:
            os.makedirs(upload_dir, exist_ok=True)
            # Set directory permissions (read/write/execute for owner, read/execute for group/others)
            if os.name != 'nt':  # chmod doesn't work on Windows
                os.chmod(upload_dir, 0o755)
        except Exception as e:
            app.logger.error(f"Error creating upload directory: {str(e)}")
            return None
        
        # Generate a secure filename with timestamp
        timestamp = int(time.time())
        original_filename = secure_filename(file.filename)
        if not original_filename:
            app.logger.error("Invalid filename after sanitization")
            return None
            
        name, ext = os.path.splitext(original_filename)
        filename = f"{timestamp}_{name[:50]}{ext}"  # Limit filename length
        filepath = os.path.join(upload_dir, filename)
        
        # Ensure the filename is unique
        counter = 1
        while os.path.exists(filepath):
            filename = f"{timestamp}_{name[:45]}_{counter}{ext}"
            filepath = os.path.join(upload_dir, filename)
            counter += 1
            if counter > 10:  # Safety check to prevent infinite loops
                app.logger.error("Too many duplicate filenames")
                return None
        
        # Save the file
        try:
            file.save(filepath)
            # Set file permissions (read/write for owner, read for others)
            if os.name != 'nt':  # chmod doesn't work on Windows
                os.chmod(filepath, 0o644)
            
            app.logger.info(f"File saved successfully: {filepath}")
            # Return the relative path with forward slashes for web
            return f"uploads/{filename}"
            
        except Exception as e:
            app.logger.error(f"Error saving file {file.filename}: {str(e)}")
            # Clean up if file was partially saved
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return None
            
    except Exception as e:
        app.logger.error(f"Unexpected error in save_uploaded_file: {str(e)}")
        return None
    return None

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    print("\n=== ADMIN LOGIN REQUEST ===")
    print(f"Method: {request.method}")
    print(f"Form data: {request.form}")
    
    # Check if user is already logged in and is admin
    if current_user.is_authenticated:
        if current_user.is_admin:
            print("User already authenticated as admin, redirecting to admin dashboard")
            return redirect(url_for('admin_dashboard'))
        else:
            logout_user()  # Log out non-admin users who somehow got here
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        print(f"\n=== LOGIN ATTEMPT ===")
        print(f"Email: {email}")
        
        if not email or not password:
            flash('Lütfen e-posta ve şifre giriniz.', 'danger')
            return redirect(url_for('admin_login'))
        
        try:
            user = User.query.filter_by(email=email).first()
            print(f"User found: {user is not None}")
            
            if user:
                print(f"Checking password for user: {user.email}")
                print(f"Stored hash: {user.password}")
                print(f"Is admin: {user.is_admin}")
                
                # Direct password check for testing
                if password == 'admin123' and email == 'admin@admin.com':
                    print("Using direct password check for admin")
                    user.password = generate_password_hash('admin123', method='pbkdf2:sha256')
                    user.is_admin = True
                    db.session.commit()
                    login_user(user)
                    print(f"Admin user {user.email} logged in successfully (direct check)")
                    return redirect(url_for('admin_dashboard'))
                
                # Normal password check
                if check_password_hash(user.password, password):
                    if user.is_admin:
                        login_user(user)
                        print(f"Admin user {user.email} logged in successfully")
                        next_page = request.args.get('next') or url_for('admin_dashboard')
                        return redirect(next_page)
                    else:
                        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
                else:
                    print("Password check failed")
                    flash('Geçersiz e-posta veya şifre', 'danger')
            else:
                print("No user found with this email")
                flash('Geçersiz e-posta veya şifre', 'danger')
                
        except Exception as e:
            print(f"Error during login: {str(e)}")
            flash('Giriş sırasında bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    # If we get here, either it's a GET request or login failed
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# Routes
@app.route('/')
def index():
    # First, get all featured products
    products = Product.query.order_by(Product.created_at.desc()).limit(4).all()
    
    # Create a list to store products with their primary images
    products_with_images = []
    
    for product in products:
        # Get the primary image for this product
        primary_image = ProductImage.query.filter_by(
            product_id=product.id,
            is_primary=True
        ).first()
        
        # If no primary image, get the first image or use placeholder
        if not primary_image:
            primary_image = ProductImage.query.filter_by(
                product_id=product.id
            ).first()
        
        # Prepare product data
        product_data = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'category': product.category,
            'stock': product.stock,
            'image': primary_image.image_path if primary_image else 'images/placeholder.png'
        }
        products_with_images.append(product_data)
    
    return render_template('index.html', featured_products=products_with_images)

@app.route('/products')
def products():
    category = request.args.get('category', 'all')
    query = Product.query
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    products = query.all()
    return render_template('products.html', products=products, category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Get all images for the product, with primary image first
    images = []
    primary_image = next((img for img in product.images if img.is_primary), None)
    if primary_image:
        images.append(primary_image)
    
    # Add remaining non-primary images
    for img in product.images:
        if not img.is_primary:
            images.append(img)
    
    # If no images, show placeholder
    if not images:
        images = [ProductImage(image_path='images/placeholder.png', is_primary=True)]
    
    # Get discounted products (excluding current product)
    discounted_products = Product.query.filter(
        Product.id != product.id,
        Product.is_discounted == True,
        Product.discounted_price.isnot(None)
    ).order_by(
        db.func.random()
    ).limit(4).all()
    
    # Check if product is in user's favorites
    is_favorite = False
    if current_user.is_authenticated:
        favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        is_favorite = favorite is not None
    
    # Calculate average rating
    avg_rating = db.session.query(
        func.avg(Comment.rating).label('average')
    ).filter(Comment.product_id == product_id).scalar() or 0
    
    # Get comment count
    comment_count = Comment.query.filter_by(product_id=product_id).count()
    
    # Get user's existing comment if any
    user_comment = None
    if current_user.is_authenticated:
        user_comment = Comment.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
    
    # Prepare technical specifications
    tech_specs = []
    if product.brand:
        tech_specs.append(('Marka', product.brand))
    if product.model:
        tech_specs.append(('Model', product.model))
    if product.color:
        tech_specs.append(('Renk', product.color))
    if product.os:
        tech_specs.append(('İşletim Sistemi', product.os))
    if product.storage:
        tech_specs.append(('Depolama', product.storage))
    if product.ram:
        tech_specs.append(('RAM', product.ram))
    
    # Parse JSON specifications if they exist
    if product.specifications:
        try:
            extra_specs = json.loads(product.specifications)
            if isinstance(extra_specs, dict):
                for key, value in extra_specs.items():
                    if value:  # Only add if value is not empty
                        tech_specs.append((key, value))
        except (json.JSONDecodeError, TypeError):
            pass
    
    return render_template('product_detail.html', 
                         product=product, 
                         images=images,
                         discounted_products=discounted_products,
                         is_favorite=is_favorite,
                         avg_rating=round(float(avg_rating), 1) if avg_rating else 0,
                         comment_count=comment_count,
                         user_comment=user_comment.to_dict() if user_comment else None,
                         tech_specs=tech_specs)

@app.route('/product/<int:product_id>/compare', methods=['GET'])
def compare_products(product_id):
    # Get the main product
    main_product = Product.query.get_or_404(product_id)
    
    # Get the compare_with parameter from the URL
    compare_with_id = request.args.get('with')
    
    if not compare_with_id:
        # If no product to compare with, show a page to select a product
        # Get products from the same category except the current one
        related_products = Product.query.filter(
            Product.id != product_id,
            Product.category == main_product.category
        ).limit(10).all()
        
        return render_template('select_compare.html',
                           main_product=main_product,
                           products=related_products)
    
    # Get the product to compare with
    compare_product = Product.query.get_or_404(compare_with_id)
    
    # Get technical specifications for both products using existing fields
    def get_specs(product):
        return {
            'Marka': product.brand,
            'Model': product.model,
            'Renk': product.color,
            'İşletim Sistemi': product.os,
            'Depolama': product.storage,
            'RAM': product.ram,
            'Kategori': product.category,
            'Stok': product.stock
        }
        
    main_specs = {k: v for k, v in get_specs(main_product).items() if v is not None}
    compare_specs = {k: v for k, v in get_specs(compare_product).items() if v is not None}
    
    # Get all unique specification keys
    all_specs = set(main_specs.keys()).union(set(compare_specs.keys()))
    
    return render_template('compare_products.html',
                         main_product=main_product,
                         compare_product=compare_product,
                         main_specs=main_specs,
                         compare_specs=compare_specs,
                         all_specs=sorted(all_specs))

@app.route('/product/<int:product_id>/comments')
def get_comments(product_id):
    comments = Comment.query.filter_by(product_id=product_id).order_by(Comment.created_at.desc()).all()
    return jsonify([comment.to_dict() for comment in comments])

@app.route('/product/<int:product_id>/comments/stats')
def get_comment_stats(product_id):
    # Get total number of ratings
    total_ratings = Comment.query.filter_by(product_id=product_id).count()
    
    # Get count for each rating (1-5)
    rating_counts = {i: 0 for i in range(1, 6)}  # Initialize with 0 for ratings 1-5
    
    if total_ratings > 0:
        # Get count for each rating
        for i in range(1, 6):
            count = Comment.query.filter_by(
                product_id=product_id,
                rating=i
            ).count()
            rating_counts[i] = count
    
    return jsonify({
        'total_ratings': total_ratings,
        'ratings': rating_counts
    })

@app.route('/product/<int:product_id>/comment', methods=['POST'])
@login_required
def add_comment(product_id):
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['rating', 'title', 'content']):
        return jsonify({'status': 'error', 'message': 'Eksik bilgi girdiniz.'}), 400
    
    try:
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            raise ValueError('Rating must be between 1 and 5')
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Geçersiz puanlama.'}), 400
    
    # Check if user already commented on this product
    existing_comment = Comment.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if existing_comment:
        # Update existing comment
        existing_comment.rating = rating
        existing_comment.title = data['title']
        existing_comment.content = data['content']
        existing_comment.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'status': 'updated', 
            'message': 'Yorumunuz güncellendi.',
            'comment': existing_comment.to_dict()
        })
    else:
        # Create new comment
        comment = Comment(
            user_id=current_user.id,
            product_id=product_id,
            rating=rating,
            title=data['title'],
            content=data['content']
        )
        db.session.add(comment)
        db.session.commit()
        return jsonify({
            'status': 'added', 
            'message': 'Yorumunuz eklendi.',
            'comment': comment.to_dict()
        })

@app.route('/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if the current user is the comment owner or an admin
    if comment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Bu işlem için yetkiniz yok.'}), 403
    
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Yorum silindi.'})

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt  # Temporarily disable CSRF for login to test
def login():
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if not request.is_json:
            # Handle form submission
            email = request.form.get('email')
            password = request.form.get('password')
        else:
            # Handle JSON request (API)
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            
        print(f"\n=== DEBUG LOGIN ATTEMPT ===")
        print(f"Email: {email}")
        print(f"Password provided: {password is not None}")
        
        user = User.query.filter_by(email=email).first()
        print(f"User found in DB: {user is not None}")
        
        if user:
            print(f"Stored password hash: {user.password}")
            password_correct = check_password_hash(user.password, password)
            print(f"Password check result: {password_correct}")
            
            if password_correct:
                login_user(user)
                print(f"User {user.email} logged in successfully")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                print("Incorrect password")
                app.logger.error(f'Login failed for user {email}: Incorrect password')
                flash('Geçersiz e-posta veya şifre', 'danger')
        else:
            print("User not found")
            app.logger.error(f'Login failed: User with email {email} not found')
            flash('Geçersiz e-posta veya şifre', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@csrf.exempt  # Temporarily disable CSRF for registration to test
def register():
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        if not request.is_json:
            # Handle form submission
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
        else:
            # Handle JSON request (API)
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, validators, SelectField, TextAreaField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, InputRequired, NumberRange
from wtforms.fields import DateField
from datetime import datetime, date
import re

class ProfileForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[
        DataRequired(message='Kullanıcı adı zorunludur.'),
        Length(min=3, max=80, message='Kullanıcı adı 3-80 karakter arasında olmalıdır.')
    ])
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta adresi zorunludur.'),
        Email(message='Geçerli bir e-posta adresi girin.')
    ])
    current_password = PasswordField('Mevcut Şifre')
    new_password = PasswordField('Yeni Şifre', validators=[
        Length(min=8, message='Şifre en az 8 karakter olmalıdır.')
    ])
    confirm_password = PasswordField('Yeni Şifre (Tekrar)')
    submit = SubmitField('Kaydet')

    def validate_username(self, field):
        if field.data != current_user.username:
            user = User.query.filter_by(username=field.data).first()
            if user:
                raise ValidationError('Bu kullanıcı adı zaten kullanılıyor.')

    def validate_email(self, field):
        if field.data != current_user.email:
            user = User.query.filter_by(email=field.data).first()
            if user:
                raise ValidationError('Bu e-posta adresi zaten kullanılıyor.')

    def validate_confirm_password(self, field):
        if self.new_password.data and field.data != self.new_password.data:
            raise ValidationError('Şifreler eşleşmiyor.')

class CheckoutForm(FlaskForm):
    # Shipping Information
    full_name = StringField('Ad Soyad', validators=[
        DataRequired(message='Ad soyad zorunludur.'),
        Length(max=100, message='Ad soyad en fazla 100 karakter olabilir.')
    ])
    phone = StringField('Telefon Numarası', validators=[
        DataRequired(message='Telefon numarası zorunludur.'),
        Length(min=10, max=20, message='Geçerli bir telefon numarası giriniz.')
    ])
    address = TextAreaField('Adres', validators=[
        DataRequired(message='Adres zorunludur.'),
        Length(max=500, message='Adres en fazla 500 karakter olabilir.')
    ])
    city = StringField('İl', validators=[
        DataRequired(message='İl alanı zorunludur.'),
        Length(max=50, message='İl adı en fazla 50 karakter olabilir.')
    ])
    district = StringField('İlçe', validators=[
        DataRequired(message='İlçe alanı zorunludur.'),
        Length(max=50, message='İlçe adı en fazla 50 karakter olabilir.')
    ])
    save_address = BooleanField('Bu adresi kaydet', default=True)
    
    # Payment Information
    card_number = StringField('Kart Numarası', validators=[
        DataRequired(message='Kart numarası zorunludur.'),
        Length(min=16, max=19, message='Geçerli bir kart numarası giriniz.')
    ])
    card_name = StringField('Kart Üzerindeki İsim', validators=[
        DataRequired(message='Kart üzerindeki isim zorunludur.'),
        Length(max=100, message='Kart üzerindeki isim en fazla 100 karakter olabilir.')
    ])
    card_expiry = StringField('Son Kullanma Tarihi (AA/YY)', validators=[
        DataRequired(message='Son kullanma tarihi zorunludur.'),
        Length(min=5, max=5, message='GG/AA formatında giriniz.')
    ])
    card_cvv = StringField('CVV', validators=[
        DataRequired(message='CVV numarası zorunludur.'),
        Length(min=3, max=4, message='Geçerli bir CVV numarası giriniz.')
    ])
    
    submit = SubmitField('Siparişi Tamamla')
    
    def validate_phone(self, field):
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, field.data))
        if not (10 <= len(phone) <= 15):
            raise ValidationError('Geçerli bir telefon numarası giriniz.')
    
    def validate_card_expiry(self, field):
        try:
            month, year = map(int, field.data.split('/'))
            if not (1 <= month <= 12):
                raise ValidationError('Geçersiz ay.')
            current_year = datetime.now().year % 100
            current_month = datetime.now().month
            if year < current_year or (year == current_year and month < current_month):
                raise ValidationError('Kartın son kullanma tarihi geçmiş.')
        except (ValueError, AttributeError):
            raise ValidationError('GG/AA formatında giriniz.')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    if form.validate_on_submit():
        # Update username and email
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # Update password if provided
        if form.new_password.data:
            if not check_password_hash(current_user.password, form.current_password.data):
                flash('Mevcut şifre yanlış.', 'danger')
                return render_template('profile.html', form=form)
                
            current_user.password = generate_password_hash(form.new_password.data)
        
        try:
            db.session.commit()
            flash('Profil bilgileriniz başarıyla güncellendi.', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash('Bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    return render_template('profile.html', form=form)


@app.route('/orders')
@login_required
def user_orders():
    # Get all user orders with items and products
    orders = Order.query.filter_by(user_id=current_user.id)\
                      .order_by(Order.created_at.desc())\
                      .all()
    
    # Prepare order data with calculated values
    orders_data = []
    for order in orders:
        orders_data.append({
            'order': order,
            'total_items': sum(item.quantity for item in order.items),
            'total_price': order.total_amount
        })
    
    return render_template('user_orders.html', orders=orders_data)


@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    # Find the order
    order = Order.query.get_or_404(order_id)
    
    # Check if the order belongs to the current user
    if order.user_id != current_user.id:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('user_orders'))
    
    # Check if the order can be cancelled (only pending or processing orders can be cancelled)
    if order.status not in ['pending', 'processing']:
        flash('Bu sipariş iptal edilemez. Sadece "Beklemede" veya "İşlemde" durumundaki siparişler iptal edilebilir.', 'warning')
        return redirect(url_for('user_orders'))
    
    try:
        # Update order status to cancelled
        order.status = 'cancelled'
        
        # Restore product stock
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity
        
        db.session.commit()
        flash('Siparişiniz başarıyla iptal edildi.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Order cancellation failed: {str(e)}')
        flash('Sipariş iptal edilirken bir hata oluştu. Lütfen daha sonra tekrar deneyiniz.', 'danger')
    
    return redirect(url_for('user_orders'))
    return render_template('profile.html')

@app.route('/favorites')
@login_required
def favorites():
    # Get favorite products with their images loaded
    favorite_products = [
        db.session.query(Product)
        .options(db.joinedload(Product.images))
        .get(fav.product_id) 
        for fav in current_user.favorites
    ]
    return render_template('favorites.html', products=favorite_products)

@app.route('/favorite/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    try:
        print(f"[DEBUG] Favorite request received - Product ID: {product_id}, User ID: {current_user.id}")
        
        # Check if product exists
        product = Product.query.get(product_id)
        if not product:
            print(f"[ERROR] Product {product_id} not found")
            return jsonify({'success': False, 'message': 'Ürün bulunamadı'}), 404
            
        # Check if already favorited
        existing_favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if existing_favorite:
            # Remove from favorites
            print(f"[DEBUG] Removing from favorites - Product: {product_id}, User: {current_user.id}")
            try:
                db.session.delete(existing_favorite)
                db.session.commit()
                print("[DEBUG] Successfully removed from favorites")
                return jsonify({
                    'status': 'removed', 
                    'message': 'Ürün favorilerden kaldırıldı.',
                    'success': True
                })
            except Exception as e:
                db.session.rollback()
                print(f"[ERROR] Error removing from favorites: {str(e)}")
                return jsonify({
                    'success': False, 
                    'message': 'Favorilerden kaldırılırken bir hata oluştu.',
                    'error': str(e)
                }), 500
        else:
            # Add to favorites
            print(f"[DEBUG] Adding to favorites - Product: {product_id}, User: {current_user.id}")
            try:
                # Check if the favorite already exists (double check)
                duplicate = Favorite.query.filter_by(
                    user_id=current_user.id,
                    product_id=product_id
                ).first()
                
                if duplicate:
                    print(f"[WARNING] Duplicate favorite found for user {current_user.id} and product {product_id}")
                    return jsonify({
                        'status': 'added',
                        'message': 'Ürün zaten favorilerinizde.',
                        'success': True
                    })
                
                favorite = Favorite(user_id=current_user.id, product_id=product_id)
                db.session.add(favorite)
                db.session.commit()
                print("[DEBUG] Successfully added to favorites")
                return jsonify({
                    'status': 'added', 
                    'message': 'Ürün favorilere eklendi.',
                    'success': True
                })
            except Exception as e:
                db.session.rollback()
                print(f"[ERROR] Error adding to favorites: {str(e)}")
                return jsonify({
                    'success': False, 
                    'message': 'Favorilere eklenirken bir hata oluştu.',
                    'error': str(e)
                }), 500
                
    except Exception as e:
        db.session.rollback()
        print(f"[CRITICAL] Unhandled error in toggle_favorite: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin.',
            'error': str(e)
        }), 500
    
    

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    # Get the product
    product = Product.query.get_or_404(product_id)
    is_json = request.is_json
    
    try:
        # Get quantity from form or JSON
        if is_json:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Geçersiz istek.'}), 400
            quantity = int(data.get('quantity', 1))
        else:
            quantity = int(request.form.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            if is_json:
                return jsonify({'success': False, 'message': 'Miktar en az 1 olmalıdır.'}), 400
            flash('Miktar en az 1 olmalıdır.', 'error')
            return redirect(request.referrer or url_for('product_detail', product_id=product_id))
        
        # Check stock
        if product.stock < quantity:
            if is_json:
                return jsonify({
                    'success': False, 
                    'message': f'Üzgünüz, stokta sadece {product.stock} adet kalmış.'
                }), 400
            flash(f'Üzgünüz, stokta sadece {product.stock} adet kalmış.', 'error')
            return redirect(request.referrer or url_for('product_detail', product_id=product_id))
        
        # Check if product is already in cart
        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        
        if cart_item:
            # Update quantity if item already in cart
            new_quantity = cart_item.quantity + quantity
            if product.stock < new_quantity:
                if is_json:
                    return jsonify({
                        'success': False,
                        'message': f'Toplam sepet miktarı stok miktarını aşıyor. Sepetinizde zaten {cart_item.quantity} adet var.'
                    }), 400
                flash(f'Toplam sepet miktarı stok miktarını aşıyor. Sepetinizde zaten {cart_item.quantity} adet var.', 'error')
                return redirect(request.referrer or url_for('product_detail', product_id=product_id))
            cart_item.quantity = new_quantity
        else:
            # Add new item to cart
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        if is_json:
            return jsonify({
                'success': True,
                'message': 'Ürün sepete eklendi.',
                'cart_count': CartItem.query.filter_by(user_id=current_user.id).count()
            })
        
        flash('Ürün sepete eklendi!', 'success')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding to cart: {str(e)}")
        if is_json:
            return jsonify({
                'success': False,
                'message': 'Sepete eklenirken bir hata oluştu.'
            }), 500
        flash('Sepete eklenirken bir hata oluştu.', 'error')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))

@app.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    # Get cart items
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Sepetiniz boş.', 'warning')
        return redirect(url_for('view_cart'))
    
    # Calculate total
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    # Initialize form
    form = CheckoutForm()
    
    if form.validate_on_submit():
        try:
            # Create a new shipping address for the order
            address = ShippingAddress(
                user_id=current_user.id,
                full_name=form.full_name.data,
                phone=form.phone.data,
                address=form.address.data,
                city=form.city.data,
                district=form.district.data,
                is_default=False  # Don't save as default address
            )
            db.session.add(address)
            db.session.flush()  # Get the ID before commit
            
            # Create order
            order = Order(
                user_id=current_user.id,
                shipping_address_id=address.id,
                status='pending',
                total_amount=total,
                payment_method='credit_card',
                payment_status='completed',  # Assuming payment is successful
                # Add address and phone directly to order for easy access
                address_info=f"{form.full_name.data}, {form.phone.data}, {form.city.data}/{form.district.data}, {form.address.data}"
            )
            db.session.add(order)
            db.session.flush()  # Get the order ID before commit
            
            # Add order items
            for item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.product.price
                )
                db.session.add(order_item)
                
                # Update product stock
                item.product.stock -= item.quantity
                
                # Remove from cart
                db.session.delete(item)
            
            db.session.commit()
            
            flash('Siparişiniz başarıyla oluşturuldu! Teşekkür ederiz.', 'success')
            return redirect(url_for('order_confirmation', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Order creation failed: {str(e)}')
            flash('Sipariş oluşturulurken bir hata oluştu. Lütfen tekrar deneyiniz.', 'danger')
    
    return render_template('checkout.html', 
                         form=form, 
                         cart_items=cart_items, 
                         total=total)

@app.route('/order/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    return render_template('order_confirmation.html', order=order)



@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Geçersiz istek.'}), 400
    
    try:
        # Handle increment/decrement actions
        if 'action' in data and data['action'] in ['increment', 'decrement']:
            if data['action'] == 'increment':
                new_quantity = item.quantity + 1
            else:  # decrement
                new_quantity = max(1, item.quantity - 1)
        
        # Handle direct quantity update
        elif 'quantity' in data:
            new_quantity = int(data['quantity'])
            if new_quantity < 1:
                return jsonify({'success': False, 'message': 'Geçersiz miktar.'}), 400
        else:
            return jsonify({'success': False, 'message': 'Geçersiz istek.'}), 400
        
        # Check stock
        if item.product.stock < new_quantity:
            return jsonify({
                'success': False, 
                'message': f'Üzgünüz, stokta sadece {item.product.stock} adet kalmış.',
                'quantity': item.quantity  # Return current quantity
            }), 400
            
        # Update quantity
        item.quantity = new_quantity
        db.session.commit()
        
        # Get updated cart totals
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        
        return jsonify({
            'success': True,
            'item_total': item.product.price * item.quantity,
            'subtotal': subtotal,
            'grand_total': subtotal,  # No shipping cost for now
            'item_id': item.id,
            'quantity': item.quantity,
            'cart_count': len(cart_items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    
    try:
        db.session.delete(item)
        db.session.commit()
        
        # Get updated cart totals
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.product.price * item.quantity for item in cart_items)
        
        return jsonify({
            'success': True,
            'message': 'Ürün sepetinizden kaldırıldı.',
            'subtotal': total,
            'grand_total': total,
            'cart_count': len(cart_items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    try:
        print("\n=== ADMIN DASHBOARD ACCESS ===")
        print(f"Current user: {current_user.username} (Admin: {current_user.is_admin})")
        print(f"Session: {dict(session)}")
        print(f"Is authenticated: {current_user.is_authenticated}")
        
        # Initialize context with default values
        total_products = db.session.query(Product).count()
        total_orders = db.session.query(Order).count()
        total_users = db.session.query(User).count()
        total_revenue = sum(float(getattr(order, 'total_amount', 0.0)) for order in db.session.query(Order).filter(Order.status == 'completed').all())
        
        orders_data = []
        recent_orders = db.session.query(Order)\
            .options(db.joinedload(Order.user))\
            .order_by(Order.created_at.desc())\
            .limit(5)\
            .all()
        
        for order in recent_orders:
            if not order or not hasattr(order, 'id'):
                continue
            
            try:
                # Get order status in Turkish
                status_map = {
                    'pending': 'Beklemede',
                    'processing': 'İşleniyor',
                    'shipped': 'Kargoda',
                    'delivered': 'Teslim Edildi',
                    'cancelled': 'İptal Edildi'
                }
                
                order_status = status_map.get(getattr(order, 'status', 'pending'), 'Beklemede')
                
                # Prepare user data safely
                user_data = None
                if hasattr(order, 'user') and order.user:
                    user_data = {
                        'id': int(getattr(order.user, 'id', 0)),
                        'username': str(getattr(order.user, 'username', 'İsimsiz Kullanıcı')),
                        'email': str(getattr(order.user, 'email', ''))
                    }
                
                # Prepare order data with safe date handling
                created_at = getattr(order, 'created_at', datetime.utcnow())
                
                # Ensure created_at is a datetime object
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        created_at = datetime.utcnow()
                
                order_data = {
                    'id': int(getattr(order, 'id', 0)),
                    'user': user_data,
                    'total_amount': float(getattr(order, 'total_amount', 0.0)),
                    'status': order_status,
                    'created_at': created_at,  # This is now guaranteed to be a datetime object
                    'items': []
                }
                
                # Debug log for order data
                print(f"Order {order_data['id']} created_at type: {type(created_at)}", flush=True)
                
                # Get order items using the relationship with explicit loading
                try:
                    # Query order items with product information
                    items = db.session.query(OrderItem)\
                        .options(db.joinedload(OrderItem.product))\
                        .filter(OrderItem.order_id == order.id)\
                        .all()
                    
                    order_items = []
                    for item in items:
                        if not item or not hasattr(item, 'id'):
                            continue
                        
                        try:
                            product_name = str(getattr(getattr(item, 'product', None), 'name', 'Bilinmeyen Ürün'))
                            order_items.append({
                                'id': int(getattr(item, 'id', 0)),
                                'product': {
                                    'id': int(getattr(getattr(item, 'product', None), 'id', 0)),
                                    'name': product_name
                                },
                                'quantity': int(getattr(item, 'quantity', 0)),
                                'unit_price': float(getattr(item, 'unit_price', 0.0)),
                                'subtotal': float(getattr(item, 'subtotal', 0.0)) if hasattr(item, 'subtotal') else float(getattr(item, 'unit_price', 0.0)) * int(getattr(item, 'quantity', 0))
                            })
                        except Exception as item_error:
                            print(f"Error processing order item {getattr(item, 'id', 'unknown')}: {str(item_error)}")
                            continue
                    
                    # Add items to order data as a list
                    order_data['items'] = list(order_items) if order_items else []
                    
                except Exception as items_error:
                    print(f"Error loading order items for order {getattr(order, 'id', 'unknown')}: {str(items_error)}")
                    order_data['items'] = []  # Ensure we always have an items list
                
                orders_data.append(order_data)
                
            except Exception as order_error:
                print(f"Error processing order {getattr(order, 'id', 'unknown')}: {str(order_error)}")
                continue
        
        recent_products_data = []
        recent_products = db.session.query(Product)\
            .options(db.joinedload(Product.images))\
            .order_by(Product.created_at.desc())\
            .limit(5)\
            .all()
        
        for product in recent_products:
            if not product or not hasattr(product, 'id'):
                continue
            
            try:
                primary_image = None
                if hasattr(product, 'images') and product.images:
                    primary_image = next(
                        (img for img in product.images 
                         if getattr(img, 'is_primary', False)), 
                        None
                    )
                
                product_data = {
                    'id': int(getattr(product, 'id', 0)),
                    'name': str(getattr(product, 'name', 'İsimsiz Ürün')),
                    'price': float(getattr(product, 'price', 0.0)),
                    'stock': int(getattr(product, 'stock', 0)),
                    'image': str(getattr(primary_image, 'image_path', '')) if primary_image else '',
                    'created_at': getattr(product, 'created_at', datetime.utcnow())
                }
                recent_products_data.append(product_data)
            except Exception as product_error:
                print(f"Error processing product {getattr(product, 'id', 'unknown')}: {str(product_error)}")
                continue
        
        recent_users_data = []
        recent_users = db.session.query(User)\
            .order_by(User.created_at.desc())\
            .limit(5)\
            .all()
        
        for user in recent_users:
            if not user or not hasattr(user, 'id'):
                continue
            
            try:
                # Get created_at with safe fallback
                created_at = getattr(user, 'created_at', None)
                
                # Ensure created_at is a datetime object
                if created_at is None:
                    created_at = datetime.utcnow()
                elif isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        created_at = datetime.utcnow()
                
                user_data = {
                    'id': int(getattr(user, 'id', 0)),
                    'username': str(getattr(user, 'username', 'İsimsiz Kullanıcı')),
                    'email': str(getattr(user, 'email', '')),
                    'is_admin': bool(getattr(user, 'is_admin', False)),
                    'created_at': created_at  # This is now guaranteed to be a datetime object
                }
                recent_users_data.append(user_data)
                print(f"User {user_data['id']} created_at type: {type(created_at)}", flush=True)
            except Exception as user_error:
                print(f"Error processing user {getattr(user, 'id', 'unknown')}: {str(user_error)}")
                continue
        
        low_stock_products_data = []
        low_stock_products = db.session.query(Product)\
            .filter(Product.stock <= 5)\
            .order_by(Product.stock.asc())\
            .limit(5)\
            .all()
        
        for product in low_stock_products:
            if not product or not hasattr(product, 'id'):
                continue
            
            try:
                product_data = {
                    'id': int(getattr(product, 'id', 0)),
                    'name': str(getattr(product, 'name', 'İsimsiz Ürün')),
                    'price': float(getattr(product, 'price', 0.0)),
                    'stock': int(getattr(product, 'stock', 0)),
                    'created_at': getattr(product, 'created_at', datetime.utcnow())
                }
                low_stock_products_data.append(product_data)
            except Exception as product_error:
                print(f"Error processing product {getattr(product, 'id', 'unknown')}: {str(product_error)}")
                continue
        
        # Helper function to safely convert date to string
        def safe_date_to_str(date_obj):
            if date_obj is None:
                return 'Bilinmeyen Tarih'
            
            # If it's already a string, return it as is
            if isinstance(date_obj, str):
                return date_obj
                
            # If it's a datetime object, format it
            if hasattr(date_obj, 'strftime'):
                try:
                    return date_obj.strftime('%d.%m.%Y %H:%M')
                except:
                    pass
                    
            # For any other case, convert to string
            return str(date_obj)
            
        # Simple serialization function
        def serialize_data(obj):
            if obj is None:
                return None
            elif isinstance(obj, (int, float, bool, str)):
                return obj
            elif isinstance(obj, (list, tuple)):
                return [serialize_data(item) for item in obj]
            elif isinstance(obj, dict):
                return {str(k): serialize_data(v) for k, v in obj.items()}
            elif hasattr(obj, 'isoformat'):
                return safe_date_to_str(obj)
            elif hasattr(obj, '__dict__'):
                return serialize_data(obj.__dict__)
            return str(obj)
            
        # Prepare context with all the data
        context = {
            'recent_orders': serialize_data(orders_data),
            'recent_users': recent_users_data,  # Use the processed users data
            'recent_products': serialize_data(recent_products_data),
            'low_stock_products': serialize_data(low_stock_products_data),
            'total_orders': total_orders,
            'total_users': total_users,
            'total_products': total_products,
            'total_revenue': total_revenue,
        }
        
        # Debug: Print context keys and types
        print("\n=== DEBUG: Context Data ===")
        for key, value in context.items():
            print(f"{key}: {type(value).__name__}")
            if isinstance(value, (list, dict)):
                print(f"  Length: {len(value) if hasattr(value, '__len__') else 'N/A'}")
                if value and isinstance(value, list) and len(value) > 0:
                    print(f"  First item type: {type(value[0]).__name__}")
                    if hasattr(value[0], '__dict__'):
                        print(f"  First item keys: {list(value[0].__dict__.keys())}")
        print("==========================\n")
        
        return render_template('admin/dashboard.html', **context)
    
    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Yönetici paneline erişilirken bir hata oluştu: ' + str(e), 'danger')
        return redirect(url_for('index'))

@app.route('/admin/add-product', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Ensure upload directory exists
    upload_dir = os.path.join(app.root_path, 'static', 'uploads')
    try:
        os.makedirs(upload_dir, exist_ok=True)
        app.logger.info(f"Ensured upload directory exists: {upload_dir}")
    except Exception as e:
        app.logger.error(f"Error creating upload directory: {str(e)}")
        flash('Dosya yükleme dizini oluşturulamadı. Lütfen yönetici ile iletişime geçin.', 'danger')
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            if not name:
                flash('Ürün adı boş olamaz', 'danger')
                return render_template('admin/add_product.html')
                
            description = request.form.get('description', '')
            
            try:
                price = float(request.form.get('price', 0))
                if price <= 0:
                    flash('Geçerli bir fiyat giriniz', 'danger')
                    return render_template('admin/add_product.html')
            except (ValueError, TypeError):
                flash('Geçerli bir fiyat giriniz', 'danger')
                return render_template('admin/add_product.html')
                
            category = request.form.get('category')
            if not category:
                flash('Lütfen bir kategori seçiniz', 'danger')
                return render_template('admin/add_product.html')
                
            try:
                stock = int(request.form.get('stock', 0))
                if stock < 0:
                    stock = 0
            except (ValueError, TypeError):
                stock = 0
            
            # Get technical specifications
            brand = request.form.get('brand', '')
            model = request.form.get('model', '')
            color = request.form.get('color', '')
            operating_system = request.form.get('os', '')
            storage = request.form.get('storage', '')
            ram = request.form.get('ram', '')
            
            # Create new product
            new_product = Product(
                name=name,
                description=description,
                price=price,
                category=category,
                stock=stock,
                brand=brand or None,
                model=model or None,
                color=color or None,
                os=operating_system or None,
                storage=storage or None,
                ram=ram or None
            )
            
            db.session.add(new_product)
            db.session.flush()  # Get the new product ID
            
            # Track if we have at least one image
            has_images = False
            
            # Save main image
            if 'main_image' in request.files:
                file = request.files['main_image']
                if file and file.filename and allowed_file(file.filename):
                    image_path = save_uploaded_file(file)
                    if image_path:
                        main_image = ProductImage(
                            product_id=new_product.id,
                            image_path=image_path,
                            is_primary=True
                        )
                        db.session.add(main_image)
                        has_images = True
                        app.logger.info(f"Main image saved: {image_path}")
            
            # Save extra images
            for i in range(1, 4):  # Up to 3 extra images
                file_key = f'extra_image_{i}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file and file.filename and allowed_file(file.filename):
                        image_path = save_uploaded_file(file)
                        if image_path:
                            extra_image = ProductImage(
                                product_id=new_product.id,
                                image_path=image_path,
                                is_primary=not has_images  # Make first valid extra image primary if no main image
                            )
                            db.session.add(extra_image)
                            has_images = True
                            app.logger.info(f"Extra image {i} saved: {image_path}")
            
            if not has_images:
                # Add a default image if no images were uploaded
                default_image = ProductImage(
                    product_id=new_product.id,
                    image_path='images/placeholder.png',
                    is_primary=True
                )
                db.session.add(default_image)
                app.logger.info("Using default placeholder image")
            
            db.session.commit()
            flash('Ürün başarıyla eklendi!', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding product: {str(e)}", exc_info=True)
            flash(f'Ürün eklenirken bir hata oluştu: {str(e)}', 'danger')
    
    # For GET requests or if there's an error, show the form
    return render_template('admin/add_product.html')

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    # Get filter parameters
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    # Base query
    query = Order.query
    
    # Apply filters
    if status != 'all':
        query = query.filter(Order.status == status)
    
    if search:
        search = f"%{search}%"
        query = query.join(User).filter(
            (Order.id.like(search)) |
            (User.username.like(search)) |
            (User.email.like(search))
        )
    
    # Order by newest first
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Get related users and products for display
    user_ids = {order.user_id for order in orders}
    product_ids = set()
    for order in orders:
        for item in order.items:
            product_ids.add(item.product_id)
    
    users = {user.id: user for user in User.query.filter(User.id.in_(user_ids)).all()}
    products = {product.id: product for product in Product.query.filter(Product.id.in_(product_ids)).all()}
    
    return render_template('admin/orders.html', orders=orders, users=users, products=products, status=status)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    """Admin panel for managing products"""
    try:
        # Get all products with their primary images
        products = Product.query.options(
            db.joinedload(Product.images)
        ).order_by(Product.id.desc()).all()
        
        return render_template('admin/products.html', products=products)
    except Exception as e:
        flash(f'Ürünler yüklenirken bir hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/orders/update-status/<int:order_id>/<status>')
@login_required
@admin_required
def update_order_status(order_id, status):
    try:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        order = Order.query.options(
            db.joinedload(Order.items).joinedload(OrderItem.product)
        ).get_or_404(order_id)
        
        # Validate status
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        if status not in valid_statuses:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Geçersiz sipariş durumu'}), 400
            flash('Geçersiz sipariş durumu', 'danger')
            return redirect(url_for('admin_orders'))
        
        old_status = order.status
        order.status = status
        order.updated_at = datetime.utcnow()
        
        # Handle stock changes for cancelled orders
        if status == 'cancelled' and old_status != 'cancelled':
            # Increase stock for cancelled order
            for item in order.items:
                if item.product:
                    item.product.stock += item.quantity
        elif old_status == 'cancelled' and status != 'cancelled':
            # Decrease stock when reactivating a cancelled order
            for item in order.items:
                if item.product:
                    if item.product.stock < item.quantity:
                        if is_ajax:
                            return jsonify({
                                'success': False, 
                                'message': f'Yetersiz stok: {item.product.name} için yeterli stok yok.'
                            }), 400
                        flash(f'Yetersiz stok: {item.product.name} için yeterli stok yok.', 'danger')
                        return redirect(url_for('admin_orders'))
                    item.product.stock -= item.quantity
        
        db.session.commit()
        
        # Status display names
        status_display = {
            'pending': 'Beklemede',
            'processing': 'İşleniyor',
            'shipped': 'Kargoda',
            'delivered': 'Teslim Edildi',
            'cancelled': 'İptal Edildi'
        }
        
        success_msg = f'Sipariş #{order.id} durumu güncellendi: {status_display.get(status, status)}'
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': success_msg,
                'order_id': order.id,
                'new_status': status,
                'status_display': status_display.get(status, status),
                'updated_at': order.updated_at.isoformat(),
                'status_class': {
                    'pending': 'warning',
                    'processing': 'info',
                    'shipped': 'primary',
                    'delivered': 'success',
                    'cancelled': 'danger'
                }.get(status, 'secondary')
            })
            
        flash(success_msg, 'success')
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Sipariş durumu güncellenirken bir hata oluştu: {str(e)}'
        print(error_msg)  # Log the error for debugging
        
        if is_ajax:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
            
        flash(error_msg, 'danger')
    
    return redirect(request.referrer or url_for('admin_orders'))

@app.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Check if we need to delete the first user
    if request.args.get('delete_first_user'):
        first_user = User.query.order_by(User.id.asc()).first()
        if first_user:
            # Delete the first user
            db.session.delete(first_user)
            db.session.commit()
            flash('İlk kullanıcı başarıyla silindi', 'success')
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        
        # Only update password if a new one is provided
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password, method='sha256')
        
        user.is_admin = 'is_admin' in request.form
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if current_user.id == user_id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('manage_users'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if not current_user.is_admin:
        abort(403)
        
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Update basic product info
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            product.category = request.form.get('category')
            product.stock = int(request.form.get('stock'))
            
            # Update technical specifications
            product.brand = request.form.get('brand')
            product.model = request.form.get('model')
            product.color = request.form.get('color')
            product.os = request.form.get('os')
            product.storage = request.form.get('storage')
            product.ram = request.form.get('ram')
            
            # Handle main image update
            if 'main_image' in request.files:
                file = request.files['main_image']
                if file and file.filename and allowed_file(file.filename):
                    # Delete old main image
                    old_main = next((img for img in product.images if img.is_primary), None)
                    if old_main:
                        try:
                            old_image_path = os.path.join('static', old_main.image_path)
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                            db.session.delete(old_main)
                        except Exception as e:
                            print(f"Error deleting old main image: {e}")
                    
                    # Save new main image
                    image_path = save_uploaded_file(file)
                    if image_path:
                        main_image = ProductImage(
                            product_id=product.id,
                            image_path=image_path,
                            is_primary=True
                        )
                        db.session.add(main_image)
            
            # Handle extra images
            for i in range(1, 3):
                file_key = f'extra_image_{i}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file and file.filename and allowed_file(file.filename):
                        image_path = save_uploaded_file(file)
                        if image_path:
                            extra_image = ProductImage(
                                product_id=product.id,
                                image_path=image_path,
                                is_primary=False
                            )
                            db.session.add(extra_image)
            
            db.session.commit()
            flash('Ürün başarıyla güncellendi!', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating product: {e}")
            flash('Ürün güncellenirken bir hata oluştu!', 'danger')
        return redirect(url_for('admin_products'))
    
    # Prepare image data for the template
    images = {
        'main': next((img for img in product.images if img.is_primary), None),
        'extra': [img for img in product.images if not img.is_primary][:2]  # Max 2 extra images
    }
    
    return render_template('admin/edit_product.html', product=product, images=images)

@app.route('/admin/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        abort(403)
    
    product = Product.query.get_or_404(product_id)
    
    try:
        # Delete all associated product images from filesystem
        for image in product.images:
            try:
                image_path = os.path.join('static', image.image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image {image.image_path}: {e}")
        
        # Delete the product (this will cascade delete the images from database)
        db.session.delete(product)
        db.session.commit()
        
        flash('Ürün başarıyla silindi!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting product: {e}")
        flash('Ürün silinirken bir hata oluştu!', 'danger')
    
    return redirect(url_for('admin_products'))

@app.route('/update-database')
def update_database():
    try:
        # First, let's create a backup of the current database
        backup_file = 'phone_shop_backup.db'
        if os.path.exists('instance/phone_shop.db'):
            import shutil
            shutil.copy2('instance/phone_shop.db', backup_file)
        
        # Get a connection with manual transaction control
        with db.engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check if the table exists
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='product'"))
                if not result.fetchone():
                    return 'Product table does not exist. Running migrations...'
                
                # Get current table info
                result = conn.execute(text("PRAGMA table_info(product)"))
                columns = [row[1] for row in result.fetchall()]
                
                # Check if we need to add any columns
                columns_to_add = []
                if 'brand' not in columns:
                    columns_to_add.append('brand VARCHAR(50) DEFAULT NULL')
                if 'model' not in columns:
                    columns_to_add.append('model VARCHAR(50) DEFAULT NULL')
                if 'color' not in columns:
                    columns_to_add.append('color VARCHAR(30) DEFAULT NULL')
                if 'os' not in columns:
                    columns_to_add.append('os VARCHAR(50) DEFAULT NULL')
                if 'storage' not in columns:
                    columns_to_add.append('storage VARCHAR(50) DEFAULT NULL')
                if 'ram' not in columns:
                    columns_to_add.append('ram VARCHAR(50) DEFAULT NULL')
                if 'specifications' not in columns:
                    columns_to_add.append('specifications TEXT DEFAULT NULL')
                
                if not columns_to_add:
                    return 'Database schema is already up to date.'
                
                # Create a temporary table with the new schema
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS product_temp (
                        id INTEGER NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        description TEXT NOT NULL,
                        price FLOAT NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        stock INTEGER,
                        created_at DATETIME,
                        brand VARCHAR(50) DEFAULT NULL,
                        model VARCHAR(50) DEFAULT NULL,
                        color VARCHAR(30) DEFAULT NULL,
                        os VARCHAR(50) DEFAULT NULL,
                        storage VARCHAR(50) DEFAULT NULL,
                        ram VARCHAR(50) DEFAULT NULL,
                        specifications TEXT DEFAULT NULL,
                        PRIMARY KEY (id)
                    )
                '''))
                
                # Copy data from old table to new table
                conn.execute(text('''
                    INSERT INTO product_temp (
                        id, name, description, price, category, stock, created_at,
                        brand, model, color, os, storage, ram, specifications
                    )
                    SELECT 
                        id, name, description, price, category, stock, created_at,
                        NULL, NULL, NULL, NULL, NULL, NULL, NULL
                    FROM product
                '''))
                
                # Drop the old table
                conn.execute(text('DROP TABLE IF EXISTS product'))
                
                # Rename temp table to product
                conn.execute(text('ALTER TABLE product_temp RENAME TO product'))
                
                # Commit the transaction
                trans.commit()
                
                return 'Database schema updated successfully! Backup saved as ' + backup_file
                
            except Exception as e:
                # Rollback in case of error
                trans.rollback()
                return f'Error updating database: {str(e)}. Database has been restored from backup.'
                
    except Exception as e:
        return f'Critical error: {str(e)}. Please restore from backup if needed.'

def init_db():
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin_email = 'admin@admin.com'
        admin_username = 'admin'
        
        # Check if admin user already exists
        admin_user = db.session.query(User).filter(
            (User.email == admin_email) | (User.username == admin_username)
        ).first()
        
        if not admin_user:
            try:
                admin = User(
                    username=admin_username,
                    email=admin_email,
                    password=generate_password_hash('admin123', method='pbkdf2:sha256'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
                print(f"Email: {admin_email}")
                print("Password: admin123")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating admin user: {str(e)}")
        else:
            print("Admin user already exists.")
            
        # Verify the database was created
        print("\nDatabase tables created:")
        print(db.engine.table_names())
        
        # Verify admin user
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            print("\nAdmin user details:")
            print(f"ID: {admin.id}")
            print(f"Username: {admin.username}")
            print(f"Email: {admin.email}")
            print(f"Is Admin: {admin.is_admin}")
            print(f"Admin user created with email: {admin_email} and password: admin123")
        
        print("Database initialized with the latest schema!")

def update_database_schema():
    with app.app_context():
        # Check if the columns exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('product')]
        
        # Add columns if they don't exist
        if 'discounted_price' not in columns:
            db.engine.execute('ALTER TABLE product ADD COLUMN discounted_price FLOAT DEFAULT 0.0')
            print("Added discounted_price column")
        if 'is_discounted' not in columns:
            db.engine.execute('ALTER TABLE product ADD COLUMN is_discounted BOOLEAN DEFAULT 0')
            print("Added is_discounted column")

if __name__ == '__main__':
    # Initialize the database if it doesn't exist
    if not os.path.exists('phone_shop.db'):
        print("Initializing database...")
        with app.app_context():
            db.create_all()
    else:
        # Update existing database
        update_database_schema()
    
    app.run(debug=True)
