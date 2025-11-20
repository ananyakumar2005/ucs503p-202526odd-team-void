import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') 
if not app.secret_key:
    app.secret_key = 'dev-key-only-for-local-development'
    print("⚠️  WARNING: Using development secret key - set SECRET_KEY environment variable for production!")

# Ensure database is initialized on startup
def initialize_app():
    from database import init_db
    init_db()
    #create_default_admin()

initialize_app()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()
    
    if user:
        return User(user['id'], user['username'], user['email'])
    return None

# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['email'])
            login_user(user_obj)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        
        conn = get_db_connection()
        
        # Check if username exists
        existing_user = conn.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing_user:
            conn.close()
            return render_template("register.html", error="Username already exists")
        
        # Create new user
        try:
            conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            
            # Get the new user
            user = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            conn.close()
            
            user_obj = User(user['id'], user['username'], user['email'])
            login_user(user_obj)
            return redirect(url_for("index"))
            
        except Exception as e:
            conn.close()
            return render_template("register.html", error="Registration failed")
    
    return render_template("register.html")

# --- Trade Offer Routes ---
@app.route("/create_trade_offer/<int:barter_id>", methods=["POST"])
@login_required
def create_trade_offer(barter_id):
    conn = get_db_connection()
    
    # Get barter details
    barter = conn.execute(
        'SELECT b.*, u.username FROM barters b JOIN users u ON b.user_id = u.id WHERE b.id = ?',
        (barter_id,)
    ).fetchone()
    
    if not barter:
        conn.close()
        return redirect(url_for("index"))
    
    name = request.form["name"]
    mobile = request.form["mobile"]
    item_description = request.form["item_description"]
    
    # Create trade offer
    conn.execute('''
        INSERT INTO trade_offers 
        (barter_id, user_id, barter_item, barter_owner, offerer_name, offerer_mobile, item_description) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (barter_id, current_user.id, barter['item'], barter['username'], name, mobile, item_description))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for("index"))

@app.route("/trade_offers")
@login_required
def view_trade_offers():
    conn = get_db_connection()
    trade_offers = conn.execute('''
        SELECT * FROM trade_offers 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return render_template("trade_offers.html", trade_offers=trade_offers)

# --- Protected Routes ---
@app.route("/")
@login_required
def index():
    conn = get_db_connection()
    
    # Get barters with usernames
    barters = conn.execute('''
        SELECT b.*, u.username 
        FROM barters b 
        JOIN users u ON b.user_id = u.id 
        WHERE b.is_active = 1 
        ORDER BY b.created_at DESC
    ''').fetchall()
    
    # Get requests with usernames
    requests = conn.execute('''
        SELECT r.*, u.username 
        FROM requests r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.is_active = 1 
        ORDER BY r.created_at DESC
    ''').fetchall()
    
    # Get user's trade offers count
    trade_offers_count = conn.execute(
        'SELECT COUNT(*) FROM trade_offers WHERE user_id = ?',
        (current_user.id,)
    ).fetchone()[0]
    
    conn.close()
    
    return render_template("index.html", 
                         barters=barters, 
                         requests=requests, 
                         username=current_user.username,
                         trade_offers_count=trade_offers_count)

@app.route("/create_barter", methods=["POST"])
@login_required
def create_barter():
    name = request.form["name"]
    mobile = request.form["mobile"]
    item = request.form["item"]
    hostel = request.form["hostel"]

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO barters (user_id, name, mobile, item, hostel) VALUES (?, ?, ?, ?, ?)',
        (current_user.id, name, mobile, item, hostel)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))

@app.route("/create_request", methods=["POST"])
@login_required
def create_request():
    name = request.form["name"]
    mobile = request.form["mobile"]
    item = request.form["item"]
    hostel = request.form["hostel"]

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO requests (user_id, name, mobile, item, hostel) VALUES (?, ?, ?, ?, ?)',
        (current_user.id, name, mobile, item, hostel)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))

@app.route("/edit_barter/<int:id>", methods=["GET", "POST"])
@login_required
def edit_barter(id):
    conn = get_db_connection()
    
    if request.method == "POST":
        conn.execute('''
            UPDATE barters SET name = ?, mobile = ?, item = ?, hostel = ? 
            WHERE id = ? AND user_id = ?
        ''', (request.form["name"], request.form["mobile"], request.form["item"], 
              request.form["hostel"], id, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    
    barter = conn.execute(
        'SELECT * FROM barters WHERE id = ? AND user_id = ?', (id, current_user.id)
    ).fetchone()
    conn.close()
    
    if not barter:
        return redirect(url_for("index"))
    
    return render_template("edit_barter.html", barter=barter)

@app.route("/edit_request/<int:id>", methods=["GET", "POST"])
@login_required
def edit_request(id):
    conn = get_db_connection()
    
    if request.method == "POST":
        conn.execute('''
            UPDATE requests SET name = ?, mobile = ?, item = ?, hostel = ? 
            WHERE id = ? AND user_id = ?
        ''', (request.form["name"], request.form["mobile"], request.form["item"], 
              request.form["hostel"], id, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    
    request_item = conn.execute(
        'SELECT * FROM requests WHERE id = ? AND user_id = ?', (id, current_user.id)
    ).fetchone()
    conn.close()
    
    if not request_item:
        return redirect(url_for("index"))
    
    return render_template("edit_request.html", request_item=request_item)

@app.route("/delete_barter/<int:id>")
@login_required
def delete_barter(id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE barters SET is_active = 0 WHERE id = ? AND user_id = ?',
        (id, current_user.id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/delete_request/<int:id>")
@login_required
def delete_request(id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE requests SET is_active = 0 WHERE id = ? AND user_id = ?',
        (id, current_user.id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# Create default admin user if not exists
def create_default_admin():
    conn = get_db_connection()
    admin = conn.execute(
        'SELECT * FROM users WHERE username = ?', ('admin',)
    ).fetchone()
    
    if not admin:
        conn.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            ('admin', 'admin@campustrade.com', generate_password_hash('admin123'))
        )
        conn.commit()
        print("✅ Default admin user created")
    
    conn.close()

create_default_admin()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)