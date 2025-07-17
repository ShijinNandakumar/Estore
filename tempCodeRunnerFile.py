@app.route('/product/<int:product_id>')
def product(product_id):
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    return render_template('product.html', product=product)