from flask import Flask
from flask_cors import CORS
from config import FLASK_PORT, FLASK_ENV
from Controler.products import product_bp
from Controler.range import range_bp
from Controler.receipts import receipt_bp
from Controler.receiption_products import reception_bp
from Controler.shopping_list import shopping_bp
from Controler.product_renge_for_user import product_range_bp
from Controler.statistics import statistics_bp
from Controler.User import user_bp
from Controler.category import category_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(user_bp)
app.register_blueprint(category_bp)
app.register_blueprint(product_bp)
app.register_blueprint(range_bp)
app.register_blueprint(receipt_bp)
app.register_blueprint(reception_bp)
app.register_blueprint(shopping_bp)
app.register_blueprint(product_range_bp)
app.register_blueprint(statistics_bp)


# Security headers on every response
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.route("/test")
def test():
    return {
        "message": "working"
    }


if __name__ == "__main__":
    print(app.url_map)
    debug = FLASK_ENV == 'development'
    app.run(debug=debug, host="0.0.0.0", port=FLASK_PORT)
