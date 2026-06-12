import os
import boto3
from flask import Flask, jsonify, request
from decimal import Decimal
from boto3.dynamodb.types import TypeSerializer

app = Flask(__name__)

# Connect to DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'cart'))

# Helper to convert floats to Decimal for DynamoDB
def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj

# Helper to convert Decimal back to float for JSON response
def convert_decimals(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    return obj

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "cart-service"
    }), 200

# Get cart for a user
@app.route('/cart/<user_id>', methods=['GET'])
def get_cart(user_id):
    try:
        response = table.get_item(
            Key={'userId': user_id}
        )
        cart = response.get('Item')
        if cart:
            return jsonify(convert_decimals(cart)), 200
        return jsonify({
            "userId": user_id,
            "items": [],
            "message": "Cart is empty"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add item to cart
@app.route('/cart', methods=['POST'])
def add_to_cart():
    try:
        data = request.get_json()
        user_id = data.get('userId')
        product_id = data.get('productId')
        product_name = data.get('productName')
        quantity = data.get('quantity', 1)
        price = data.get('price')

        if not user_id or not product_id:
            return jsonify({
                "error": "userId and productId are required"
            }), 400

        # Get existing cart or create new one
        response = table.get_item(Key={'userId': user_id})
        cart = response.get('Item', {
            'userId': user_id,
            'items': []
        })

        # Check if product already in cart
        items = cart.get('items', [])
        existing = next(
            (i for i in items if i['productId'] == product_id),
            None
        )

        if existing:
            existing['quantity'] = existing['quantity'] + quantity
        else:
            items.append(convert_floats({
                'productId': product_id,
                'productName': product_name,
                'quantity': quantity,
                'price': price
            }))

        cart['items'] = items

        # Save to DynamoDB
        table.put_item(Item=convert_floats(cart))

        return jsonify({
            "message": "Item added to cart",
            "cart": convert_decimals(cart)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Remove item from cart
@app.route('/cart/<user_id>/<product_id>',
           methods=['DELETE'])
def remove_from_cart(user_id, product_id):
    try:
        response = table.get_item(Key={'userId': user_id})
        cart = response.get('Item')

        if not cart:
            return jsonify({"error": "Cart not found"}), 404

        cart['items'] = [
            i for i in cart.get('items', [])
            if i['productId'] != product_id
        ]

        table.put_item(Item=convert_floats(cart))

        return jsonify({
            "message": "Item removed from cart",
            "cart": convert_decimals(cart)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)