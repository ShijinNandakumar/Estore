from flask import Flask, render_template, redirect, url_for, request, session, flash
import json
import os
import datetime


from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        users = load_users()
        current_user = next((u for u in users if u['username'] == session.get('user')), None)
        if not current_user or not current_user.get('is_admin'):
            flash("Admin access only.")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

BOOKINGS_FILE = 'bookings.json'


def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return []
    with open(BOOKINGS_FILE, 'r') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                return []
        except json.JSONDecodeError:
            # file is empty or corrupted
            return []

def save_bookings(bookings):
    with open('bookings.json', 'w') as f:
        json.dump(bookings, f)


def load_users():
    try:
        with open('users.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f)


app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key_here'  # Change this to a strong secret key

@app.context_processor
def inject_current_user():
    users = load_users()
    current_user = next((u for u in users if u['username'] == session.get('user')), None)
    return dict(current_user=current_user)


# Dummy user credentials
USER = {'username': 'admin', 'password': 'pass123'}

# Load product data from JSON
def load_products():
    with open('products.json') as f:
        return json.load(f)
    

@app.route('/')
def index():
    with open('categories.json') as f:
        categories = json.load(f)
    return render_template('index.html', categories=categories)


@app.route('/category/<category_name>')
def category_products(category_name):
    with open('products.json') as f:
        products = json.load(f)
    filtered_products = [p for p in products if p['category'].lower() == category_name.lower()]
    return render_template('category_products.html', products=filtered_products, category=category_name)




@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    products = load_products()
    return render_template('admin_dashboard.html', products=products)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])

        products = load_products()

        # Generate new product id (max existing id + 1)
        new_id = max((p['id'] for p in products), default=0) + 1

        new_product = {
            'id': new_id,
            'name': name,
            'price': price,
            'quantity': quantity
        }
        products.append(new_product)

        # Save updated products
        with open('products.json', 'w') as f:
            json.dump(products, f)

        flash('Product added successfully.')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    products = load_products()
    product = next((p for p in products if p['id'] == product_id), None)

    if not product:
        flash('Product not found.')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        product['name'] = request.form['name']
        product['price'] = float(request.form['price'])
        product['quantity'] = int(request.form['quantity'])

        with open('products.json', 'w') as f:
            json.dump(products, f)

        flash('Product updated successfully.')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_product.html', product=product)



@app.route('/product/<int:product_id>')
def product(product_id):
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)

    if product is None:
        return "<h2>Product not found</h2>", 404

    return render_template('product.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    pid = str(product_id)
    cart[pid] = cart.get(pid, 0) + 1
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    pid = str(product_id)
    if pid in cart:
        cart.pop(pid)
        session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    products = load_products()
    cart = session.get('cart', {})
    cart_items = []
    for product in products:
        pid = str(product['id'])
        if pid in cart:
            p = product.copy()
            p['quantity'] = cart[pid]
            p['total_price'] = p['quantity'] * p['price']
            cart_items.append(p)
    total = sum(item['total_price'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/book', methods=['POST'])
def book():
    if 'user' not in session:
        flash("Please login to book.")
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('cart'))

    bookings = load_bookings()
    booking = {
        'username': session['user'],
        'items': cart,
        'timestamp': datetime.datetime.now().isoformat()
    }
    bookings.append(booking)
    save_bookings(bookings)

    session.pop('cart', None)
    flash("Booking successful!")
    return render_template('booking_success.html')

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    bookings = load_bookings()
    products = load_products()
    # Optional: enrich bookings with product details
    return render_template('admin_bookings.html', bookings=bookings, products=products)

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    products = load_products()
    products = [p for p in products if p['id'] != product_id]
    with open('products.json', 'w') as f:
        json.dump(products, f)
    flash("Product deleted successfully.")
    return redirect(url_for('admin_dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)
        if user:
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()
        if any(u['username'] == username for u in users):
            flash("Username already exists")
            return redirect(url_for('register'))

        users.append({'username': username, 'password': password, 'is_admin': False})
        save_users(users)
        flash("Registration successful. Please log in.")
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# Test route to check CSS loading
@app.route('/test-style')
def test_style():
    return '''
    <html>
      <head>
        <link rel="stylesheet" href="/static/style.css">
      </head>
      <body>
        <h1>Hello with Style</h1>
      </body>
    </html>
    '''


if __name__ == '__main__':
    print(f"Static folder path: {os.path.abspath(app.static_folder)}")
    app.run(debug=True)


