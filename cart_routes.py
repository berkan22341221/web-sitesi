from flask import jsonify, request
from flask_login import login_required, current_user
from . import db
from .models import Product, CartItem

def init_cart_routes(app):
    @app.route('/api/cart/add/<int:product_id>', methods=['POST'])
    @login_required
    def add_to_cart(product_id):
        # Get the product
        product = Product.query.get_or_404(product_id)
        
        # Get quantity from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek.'}), 400
            
        try:
            quantity = int(data.get('quantity', 1))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'Geçersiz miktar.'}), 400
        
        # Validate quantity
        if quantity < 1:
            return jsonify({'success': False, 'message': 'Miktar en az 1 olmalıdır.'}), 400
        
        # Check stock
        if product.stock < quantity:
            return jsonify({
                'success': False, 
                'message': f'Üzgünüz, stokta sadece {product.stock} adet kalmış.'
            }), 400
        
        try:
            # Check if product already in cart
            cart_item = CartItem.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
            
            if cart_item:
                # Update quantity if item already in cart
                new_quantity = cart_item.quantity + quantity
                if product.stock < new_quantity:
                    return jsonify({
                        'success': False,
                        'message': f'Toplam sepet miktarı stok miktarını aşıyor. Sepetinizde zaten {cart_item.quantity} adet var.'
                    }), 400
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
            
            # Get updated cart count
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
            
            return jsonify({
                'success': True,
                'message': 'Ürün sepete eklendi.',
                'cart_count': cart_count
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding to cart: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Sepete eklenirken bir hata oluştu.'
            }), 500
