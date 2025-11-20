import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') 
if not app.secret_key:
    app.secret_key = 'dev-key-only-for-local-development'
    print("⚠️  WARNING: Using development secret key - set SECRET_KEY environment variable for production!")

# PostgreSQL configuration
def get_db_connection():
    # For Render PostgreSQL
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Parse the database URL for Render
        parsed_url = urllib.parse.urlparse(database_url)
        conn = psycopg2.connect(
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port,
            sslmode='require'
        )
    else:
        # Local development fallback
        conn = psycopg2.connect(
            database='campustrade',
            user='postgres',
            password='password',
            host='localhost',
            port='5432'
        )
    
    return conn

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
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user:
        return User(user['id'], user['username'], user['email'])
    return None

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Barters table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS barters (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            mobile VARCHAR(20) NOT NULL,
            item TEXT NOT NULL,
            hostel VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Requests table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            mobile VARCHAR(20) NOT NULL,
            item TEXT NOT NULL,
            hostel VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Trade offers table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trade_offers (
            id SERIAL PRIMARY KEY,
            barter_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            barter_item TEXT NOT NULL,
            barter_owner VARCHAR(100) NOT NULL,
            offerer_name VARCHAR(100) NOT NULL,
            offerer_mobile VARCHAR(20) NOT NULL,
            item_description TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (barter_id) REFERENCES barters (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Received trade offers table (for item owners)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS received_trade_offers (
            id SERIAL PRIMARY KEY,
            trade_offer_id INTEGER NOT NULL,
            receiver_user_id INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trade_offer_id) REFERENCES trade_offers (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

# Initialize database on startup
init_db()

# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
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
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if username exists
        cur.execute('SELECT id FROM users WHERE username = %s', (username,))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            conn.close()
            return render_template("register.html", error="Username already exists")
        
        # Create new user
        try:
            cur.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id',
                (username, email, generate_password_hash(password))
            )
            user_id = cur.fetchone()['id']
            conn.commit()
            
            # Get the new user
            cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            user_obj = User(user['id'], user['username'], user['email'])
            login_user(user_obj)
            return redirect(url_for("index"))
            
        except Exception as e:
            cur.close()
            conn.close()
            return render_template("register.html", error="Registration failed")
    
    return render_template("register.html")

# --- Trade Offer Routes ---
@app.route("/create_trade_offer/<int:barter_id>", methods=["POST"])
@login_required
def create_trade_offer(barter_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get barter details and owner info
    cur.execute('''
        SELECT b.*, u.username, u.id as owner_id 
        FROM barters b 
        JOIN users u ON b.user_id = u.id 
        WHERE b.id = %s AND b.is_active = TRUE
    ''', (barter_id,))
    
    barter = cur.fetchone()
    
    if not barter:
        cur.close()
        conn.close()
        return redirect(url_for("index"))
    
    name = request.form["name"]
    mobile = request.form["mobile"]
    item_description = request.form["item_description"]
    
    # Create trade offer
    cur.execute('''
        INSERT INTO trade_offers 
        (barter_id, user_id, barter_item, barter_owner, offerer_name, offerer_mobile, item_description) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (barter_id, current_user.id, barter['item'], barter['username'], name, mobile, item_description))
    
    trade_offer_id = cur.fetchone()['id']
    
    # Create received trade offer for the item owner
    cur.execute('''
        INSERT INTO received_trade_offers (trade_offer_id, receiver_user_id)
        VALUES (%s, %s)
    ''', (trade_offer_id, barter['owner_id']))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for("index"))

@app.route("/trade_offers")
@login_required
def view_trade_offers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get trade offers made by current user
    cur.execute('''
        SELECT * FROM trade_offers 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    ''', (current_user.id,))
    trade_offers = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template("trade_offers.html", trade_offers=trade_offers)

@app.route("/received_offers")
@login_required
def view_received_offers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get trade offers received by current user
    cur.execute('''
        SELECT toff.*, ro.status as received_status, ro.id as received_offer_id
        FROM received_trade_offers ro
        JOIN trade_offers toff ON ro.trade_offer_id = toff.id
        WHERE ro.receiver_user_id = %s 
        ORDER BY ro.created_at DESC
    ''', (current_user.id,))
    received_offers = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template("received_offers.html", received_offers=received_offers)

@app.route("/update_offer_status/<int:received_offer_id>/<string:status>")
@login_required
def update_offer_status(received_offer_id, status):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Update received offer status
    cur.execute('''
        UPDATE received_trade_offers 
        SET status = %s 
        WHERE id = %s AND receiver_user_id = %s
    ''', (status, received_offer_id, current_user.id))
    
    # Also update the main trade offer status
    if status in ['accepted', 'rejected']:
        cur.execute('''
            UPDATE trade_offers 
            SET status = %s 
            WHERE id = (
                SELECT trade_offer_id FROM received_trade_offers WHERE id = %s
            )
        ''', (status, received_offer_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for("view_received_offers"))

# --- Protected Routes ---
@app.route("/")
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get barters with usernames
    cur.execute('''
        SELECT b.*, u.username 
        FROM barters b 
        JOIN users u ON b.user_id = u.id 
        WHERE b.is_active = TRUE 
        ORDER BY b.created_at DESC
    ''')
    barters = cur.fetchall()
    
    # Get requests with usernames
    cur.execute('''
        SELECT r.*, u.username 
        FROM requests r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.is_active = TRUE 
        ORDER BY r.created_at DESC
    ''')
    requests = cur.fetchall()
    
    # Get user's trade offers count
    cur.execute('SELECT COUNT(*) FROM trade_offers WHERE user_id = %s', (current_user.id,))
    trade_offers_count = cur.fetchone()['count']
    
    # Get received offers count
    cur.execute('SELECT COUNT(*) FROM received_trade_offers WHERE receiver_user_id = %s AND status = %s', 
                (current_user.id, 'pending'))
    pending_received_offers_count = cur.fetchone()['count']
    
    cur.close()
    conn.close()
    
    return render_template("index.html", 
                         barters=barters, 
                         requests=requests, 
                         username=current_user.username,
                         trade_offers_count=trade_offers_count,
                         pending_received_offers_count=pending_received_offers_count)

@app.route("/create_barter", methods=["POST"])
@login_required
def create_barter():
    name = request.form["name"]
    mobile = request.form["mobile"]
    item = request.form["item"]
    hostel = request.form["hostel"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO barters (user_id, name, mobile, item, hostel) VALUES (%s, %s, %s, %s, %s)',
        (current_user.id, name, mobile, item, hostel)
    )
    conn.commit()
    cur.close()
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
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO requests (user_id, name, mobile, item, hostel) VALUES (%s, %s, %s, %s, %s)',
        (current_user.id, name, mobile, item, hostel)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("index"))

@app.route("/edit_barter/<int:id>", methods=["GET", "POST"])
@login_required
def edit_barter(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == "POST":
        cur.execute('''
            UPDATE barters SET name = %s, mobile = %s, item = %s, hostel = %s 
            WHERE id = %s AND user_id = %s
        ''', (request.form["name"], request.form["mobile"], request.form["item"], 
              request.form["hostel"], id, current_user.id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("index"))
    
    cur.execute('SELECT * FROM barters WHERE id = %s AND user_id = %s', (id, current_user.id))
    barter = cur.fetchone()
    cur.close()
    conn.close()
    
    if not barter:
        return redirect(url_for("index"))
    
    return render_template("edit_barter.html", barter=barter)

@app.route("/edit_request/<int:id>", methods=["GET", "POST"])
@login_required
def edit_request(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == "POST":
        cur.execute('''
            UPDATE requests SET name = %s, mobile = %s, item = %s, hostel = %s 
            WHERE id = %s AND user_id = %s
        ''', (request.form["name"], request.form["mobile"], request.form["item"], 
              request.form["hostel"], id, current_user.id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("index"))
    
    cur.execute('SELECT * FROM requests WHERE id = %s AND user_id = %s', (id, current_user.id))
    request_item = cur.fetchone()
    cur.close()
    conn.close()
    
    if not request_item:
        return redirect(url_for("index"))
    
    return render_template("edit_request.html", request_item=request_item)

@app.route("/delete_barter/<int:id>")
@login_required
def delete_barter(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE barters SET is_active = FALSE WHERE id = %s AND user_id = %s',
        (id, current_user.id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))

@app.route("/delete_request/<int:id>")
@login_required
def delete_request(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE requests SET is_active = FALSE WHERE id = %s AND user_id = %s',
        (id, current_user.id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))

# Create default admin user if not exists
def create_default_admin():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM users WHERE username = %s', ('admin',))
    admin = cur.fetchone()
    
    if not admin:
        cur.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
            ('admin', 'admin@campustrade.com', generate_password_hash('admin123'))
        )
        conn.commit()
        print("✅ Default admin user created")
    
    cur.close()
    conn.close()

create_default_admin()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)