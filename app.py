from flask import Flask
from flask_cors import CORS
from config import FLASK_PORT, FLASK_ENV
from Controler.products import product_bp
from Controler.range import range_bp
from Controler.receipts import receipt_bp
from Controler.receiption_products import reception_bp
from Controler.shopping_list import shopping_bp
from Controler.product_renge_for_user import product_range_bp

app = Flask(__name__)
CORS(app)

from Controler.User import user_bp
from Controler.category import category_bp

app.register_blueprint(user_bp)
app.register_blueprint(category_bp)
app.register_blueprint(product_bp)

import sys
print("Python executable:", sys.executable)

# RANGE
app.register_blueprint(range_bp)

# RECEIPTS
app.register_blueprint(receipt_bp)

# RECEPTION PRODUCTS
app.register_blueprint(reception_bp)

# SHOPPING LIST
app.register_blueprint(shopping_bp)

app.register_blueprint(product_range_bp)


@app.route("/test")
def test():
    return {
        "message": "working"
    }


if __name__ == "__main__":
    print(app.url_map)
    debug = FLASK_ENV == 'development'
    app.run(debug=debug, host="0.0.0.0", port=FLASK_PORT)


