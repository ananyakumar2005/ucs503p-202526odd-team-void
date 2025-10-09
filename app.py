import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-2024")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# In-memory user storage (replace with database in production)
users = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'id': 1,
        'email': 'admin@campustrade.com'
    }
}

# In-memory storage for barters and requests
barters = []
requests = []
barter_id = 1
request_id = 1

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = list(users.keys())[list(users.values()).index(user_data)]
        self.email = user_data['email']

@login_manager.user_loader
def load_user(user_id):
    user_data = next((data for data in users.values() if data['id'] == int(user_id)), None)
    if user_data:
        return User(user_data)
    return None

# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        user_data = users.get(username)
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
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
        
        if username in users:
            return render_template("register.html", error="Username already exists")
        
        # Create new user
        new_user_id = max([user['id'] for user in users.values()]) + 1
        users[username] = {
            'id': new_user_id,
            'password': generate_password_hash(password),
            'email': email
        }
        
        # Auto-login after registration
        user = User(users[username])
        login_user(user)
        return redirect(url_for("index"))
    
    return render_template("register.html")

# --- Protected Routes ---
@app.route("/")
@login_required
def index():
    return render_template("index.html", 
                         barters=barters, 
                         requests=requests, 
                         username=current_user.username)

@app.route("/create_barter", methods=["POST"])
@login_required
def create_barter():
    global barter_id
    name = request.form["name"]
    mobile = request.form["mobile"]
    item = request.form["item"]
    hostel = request.form["hostel"]

    new_barter = {
        "id": barter_id,
        "name": name,
        "mobile": mobile,
        "item": item,
        "hostel": hostel,
        "created_by": current_user.username
    }
    barters.append(new_barter)
    barter_id += 1

    return redirect(url_for("index"))

@app.route("/create_request", methods=["POST"])
@login_required
def create_request():
    global request_id
    name = request.form["name"]
    mobile = request.form["mobile"]
    item = request.form["item"]
    hostel = request.form["hostel"]

    new_request = {
        "id": request_id,
        "name": name,
        "mobile": mobile,
        "item": item,
        "hostel": hostel,
        "created_by": current_user.username
    }
    requests.append(new_request)
    request_id += 1

    return redirect(url_for("index"))

@app.route("/edit_barter/<int:id>", methods=["GET", "POST"])
@login_required
def edit_barter(id):
    barter = next((b for b in barters if b["id"] == id), None)
    if not barter:
        return redirect(url_for("index"))
    
    # Check if user owns this barter
    if barter.get("created_by") != current_user.username:
        return redirect(url_for("index"))

    if request.method == "POST":
        barter["name"] = request.form["name"]
        barter["mobile"] = request.form["mobile"]
        barter["item"] = request.form["item"]
        barter["hostel"] = request.form["hostel"]
        return redirect(url_for("index"))

    return render_template("edit_barter.html", barter=barter)

@app.route("/edit_request/<int:id>", methods=["GET", "POST"])
@login_required
def edit_request(id):
    request_item = next((r for r in requests if r["id"] == id), None)
    if not request_item:
        return redirect(url_for("index"))
    
    # Check if user owns this request
    if request_item.get("created_by") != current_user.username:
        return redirect(url_for("index"))

    if request.method == "POST":
        request_item["name"] = request.form["name"]
        request_item["mobile"] = request.form["mobile"]
        request_item["item"] = request.form["item"]
        request_item["hostel"] = request.form["hostel"]
        return redirect(url_for("index"))

    return render_template("edit_request.html", request_item=request_item)

@app.route("/delete_barter/<int:id>")
@login_required
def delete_barter(id):
    global barters
    barter = next((b for b in barters if b["id"] == id), None)
    if barter and barter.get("created_by") == current_user.username:
        barters = [b for b in barters if b["id"] != id]
    return redirect(url_for("index"))

@app.route("/delete_request/<int:id>")
@login_required
def delete_request(id):
    global requests
    request_item = next((r for r in requests if r["id"] == id), None)
    if request_item and request_item.get("created_by") == current_user.username:
        requests = [r for r in requests if r["id"] != id]
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)