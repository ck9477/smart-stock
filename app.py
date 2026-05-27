from flask import Flask
from Controler.products import product_bp
from Controler.range import range_bp
from Controler.receipts import receipt_bp
from Controler.receiption_products import reception_bp
from Controler.shopping_list import shopping_bp
from Controler.product_renge_for_user import product_range_bp

app = Flask(__name__)
from Controler.User import user_bp

app.register_blueprint(user_bp)
from Controler.category import category_bp

app.register_blueprint(category_bp)
app.register_blueprint(product_bp)

# RANGE
app.register_blueprint(range_bp)

# RECEIPTS
app.register_blueprint(receipt_bp)

# RECEPTION PRODUCTS
app.register_blueprint(reception_bp)

# SHOPPING LIST
app.register_blueprint(shopping_bp)

app.register_blueprint(product_range_bp)

if __name__ == "__main__":
    app.run(debug=True)
@app.route("/test")
def test():
    return {
        "message": "working"
    }

if __name__ == "__main__":

    app.run(debug=True)

print(app.url_map)
