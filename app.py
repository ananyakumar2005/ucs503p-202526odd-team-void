import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-only-for-local-development')

# PostgreSQL configuration
def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # For Render PostgreSQL
        conn = psycopg2.connect(
            database_url,
            sslmode='require'
        )
        return conn
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
    
    try:
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
        
        # Received trade offers table
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
        print("✅ Database tables created successfully")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
    finally:
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
            return render_template("register.html", error=f"Registration failed: {str(e)}")
    
    return render_template("register.html")

# --- Trade Offer Routes ---
@app.route("/create_trade_offer/<int:barter_id>", methods=["POST"])
@login_required
def create_trade_offer(barter_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
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
        
        print(f"Creating trade offer for barter {barter_id} by user {current_user.id}")
        print(f"Barter owner: {barter['owner_id']}")
        
        # Create trade offer
        cur.execute('''
            INSERT INTO trade_offers 
            (barter_id, user_id, barter_item, barter_owner, offerer_name, offerer_mobile, item_description) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (barter_id, current_user.id, barter['item'], barter['username'], name, mobile, item_description))
        
        trade_offer_id = cur.fetchone()['id']
        print(f"Created trade offer with ID: {trade_offer_id}")
        
        # Create received trade offer for the item owner
        cur.execute('''
            INSERT INTO received_trade_offers (trade_offer_id, receiver_user_id)
            VALUES (%s, %s)
        ''', (trade_offer_id, barter['owner_id']))
        
        conn.commit()
        print("Trade offer committed successfully")
        
    except Exception as e:
        print(f"❌ Error creating trade offer: {e}")
        conn.rollback()
        # Return error for debugging
        return f"Error: {str(e)}", 500
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for("index"))

@app.route("/trade_offers")
@login_required
def view_trade_offers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get trade offers made by current user with barter details
        cur.execute('''
            SELECT 
                toff.*,
                b.item as original_barter_item,
                b.hostel as barter_hostel,
                u_owner.username as barter_owner_username,
                ro.status as received_status
            FROM trade_offers toff
            JOIN barters b ON toff.barter_id = b.id
            JOIN users u_owner ON b.user_id = u_owner.id
            LEFT JOIN received_trade_offers ro ON toff.id = ro.trade_offer_id
            WHERE toff.user_id = %s 
            ORDER BY toff.created_at DESC
        ''', (current_user.id,))
        
        trade_offers = cur.fetchall()
        
        print(f"Found {len(trade_offers)} trade offers made by user {current_user.id}")
        
    except Exception as e:
        print(f"❌ Error fetching trade offers: {e}")
        trade_offers = []
    finally:
        cur.close()
        conn.close()
    
    return render_template("trade_offers.html", trade_offers=trade_offers)

@app.route("/received_offers")
@login_required
def view_received_offers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get trade offers received by current user with all details
        cur.execute('''
            SELECT 
                toff.*,
                ro.status as received_status, 
                ro.id as received_offer_id,
                b.item as original_barter_item,
                b.hostel as barter_hostel,
                u_offerer.username as offerer_username
            FROM received_trade_offers ro
            JOIN trade_offers toff ON ro.trade_offer_id = toff.id
            JOIN barters b ON toff.barter_id = b.id
            JOIN users u_offerer ON toff.user_id = u_offerer.id
            WHERE ro.receiver_user_id = %s 
            ORDER BY ro.created_at DESC
        ''', (current_user.id,))
        
        received_offers = cur.fetchall()
        
        print(f"Found {len(received_offers)} received offers for user {current_user.id}")
        for offer in received_offers:
            print(f"Offer ID: {offer['id']}, Status: {offer['received_status']}")
            
    except Exception as e:
        print(f"❌ Error fetching received offers: {e}")
        received_offers = []
    finally:
        cur.close()
        conn.close()
    
    return render_template("received_offers.html", received_offers=received_offers)

@app.route("/update_offer_status/<int:received_offer_id>/<string:status>")
@login_required
def update_offer_status(received_offer_id, status):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print(f"Updating offer {received_offer_id} to status: {status}")
        
        # Update received offer status
        cur.execute('''
            UPDATE received_trade_offers 
            SET status = %s 
            WHERE id = %s AND receiver_user_id = %s
            RETURNING trade_offer_id
        ''', (status, received_offer_id, current_user.id))
        
        result = cur.fetchone()
        if result:
            trade_offer_id = result['trade_offer_id']
            print(f"Updated received offer, trade_offer_id: {trade_offer_id}")
            
            # Also update the main trade offer status
            if status in ['accepted', 'rejected']:
                cur.execute('''
                    UPDATE trade_offers 
                    SET status = %s 
                    WHERE id = %s
                ''', (status, trade_offer_id))
                print(f"Updated trade_offer {trade_offer_id} to {status}")
        
        conn.commit()
        print("Status update committed successfully")
        
    except Exception as e:
        print(f"❌ Error updating offer status: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for("view_received_offers"))

# --- Protected Routes ---
@app.route("/")
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
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
        
        # Get received offers count (pending only)
        cur.execute('''
            SELECT COUNT(*) FROM received_trade_offers 
            WHERE receiver_user_id = %s AND status = 'pending'
        ''', (current_user.id,))
        pending_received_offers_count = cur.fetchone()['count']
        
        print(f"User {current_user.id} - Trade offers made: {trade_offers_count}, Pending received: {pending_received_offers_count}")
        
    except Exception as e:
        print(f"Error loading index data: {e}")
        barters = []
        requests = []
        trade_offers_count = 0
        pending_received_offers_count = 0
    finally:
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
    
    try:
        cur.execute(
            'INSERT INTO barters (user_id, name, mobile, item, hostel) VALUES (%s, %s, %s, %s, %s)',
            (current_user.id, name, mobile, item, hostel)
        )
        conn.commit()
    except Exception as e:
        print(f"Error creating barter: {e}")
        conn.rollback()
    finally:
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
    
    try:
        cur.execute(
            'INSERT INTO requests (user_id, name, mobile, item, hostel) VALUES (%s, %s, %s, %s, %s)',
            (current_user.id, name, mobile, item, hostel)
        )
        conn.commit()
    except Exception as e:
        print(f"Error creating request: {e}")
        conn.rollback()
    finally:
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

# Debug route to check database state
@app.route("/debug/offers")
@login_required
def debug_offers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check all trade offers
    cur.execute('SELECT * FROM trade_offers ORDER BY created_at DESC')
    all_offers = cur.fetchall()
    
    # Check received offers for current user
    cur.execute('SELECT * FROM received_trade_offers WHERE receiver_user_id = %s', (current_user.id,))
    user_received = cur.fetchall()
    
    # Check barters
    cur.execute('SELECT * FROM barters WHERE is_active = TRUE')
    active_barters = cur.fetchall()
    
    cur.close()
    conn.close()
    
    debug_html = f"""
    <h1>Debug Info - User {current_user.id} ({current_user.username})</h1>
    
    <h2>All Trade Offers ({len(all_offers)})</h2>
    <table border="1">
        <tr>
            <th>ID</th>
            <th>Barter ID</th>
            <th>User ID</th>
            <th>Barter Item</th>
            <th>Barter Owner</th>
            <th>Offerer Name</th>
            <th>Status</th>
            <th>Created</th>
        </tr>
    """
    
    for offer in all_offers:
        debug_html += f"""
        <tr>
            <td>{offer['id']}</td>
            <td>{offer['barter_id']}</td>
            <td>{offer['user_id']}</td>
            <td>{offer['barter_item']}</td>
            <td>{offer['barter_owner']}</td>
            <td>{offer['offerer_name']}</td>
            <td>{offer['status']}</td>
            <td>{offer['created_at']}</td>
        </tr>
        """
    
    debug_html += "</table>"
    
    debug_html += f"""
    <h2>Your Received Offers ({len(user_received)})</h2>
    <table border="1">
        <tr>
            <th>ID</th>
            <th>Trade Offer ID</th>
            <th>Receiver User ID</th>
            <th>Status</th>
            <th>Created</th>
        </tr>
    """
    
    for received in user_received:
        debug_html += f"""
        <tr>
            <td>{received['id']}</td>
            <td>{received['trade_offer_id']}</td>
            <td>{received['receiver_user_id']}</td>
            <td>{received['status']}</td>
            <td>{received['created_at']}</td>
        </tr>
        """
    
    debug_html += "</table>"
    
    debug_html += f"""
    <h2>Active Barters ({len(active_barters)})</h2>
    <table border="1">
        <tr>
            <th>ID</th>
            <th>User ID</th>
            <th>Item</th>
            <th>Name</th>
            <th>Hostel</th>
        </tr>
    """
    
    for barter in active_barters:
        debug_html += f"""
        <tr>
            <td>{barter['id']}</td>
            <td>{barter['user_id']}</td>
            <td>{barter['item']}</td>
            <td>{barter['name']}</td>
            <td>{barter['hostel']}</td>
        </tr>
        """
    
    debug_html += "</table>"
    
    return debug_html

# Create default admin user if not exists
def create_default_admin():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute('SELECT * FROM users WHERE username = %s', ('admin',))
        admin = cur.fetchone()
        
        if not admin:
            cur.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
                ('admin', 'admin@campustrade.com', generate_password_hash('admin123'))
            )
            conn.commit()
            print("✅ Default admin user created")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        cur.close()
        conn.close()

create_default_admin()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)