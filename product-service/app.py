import os
import boto3
from flask import Flask, jsonify
from boto3.dynamodb.conditions import Key

app = Flask(__name__)

# Connect to DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'products'))

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "product-catalog"
    }), 200

# Get all products
@app.route('/products', methods=['GET'])
def get_products():
    try:
        response = table.scan()
        products = response.get('Items', [])
        return jsonify({
            "products": products,
            "count": len(products)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get single product by ID
@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        response = table.get_item(
            Key={'id': product_id}
        )
        product = response.get('Item')
        if product:
            return jsonify(product), 200
        return jsonify({"error": "Product not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)