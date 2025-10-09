import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# In-memory storage for barters and requests
barters = []
requests = []
barter_id = 1
request_id = 1

# --- Home Page: Toggle between barters and requests ---
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", barters=barters, requests=requests)

# --- Create New Barter ---
@app.route("/create_barter", methods=["POST"])
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
        "hostel": hostel
    }
    barters.append(new_barter)
    barter_id += 1

    return redirect(url_for("index"))

# --- Create New Request ---
@app.route("/create_request", methods=["POST"])
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
        "hostel": hostel
    }
    requests.append(new_request)
    request_id += 1

    return redirect(url_for("index"))

# --- Edit Barter ---
@app.route("/edit_barter/<int:id>", methods=["GET", "POST"])
def edit_barter(id):
    barter = next((b for b in barters if b["id"] == id), None)
    if not barter:
        return redirect(url_for("index"))

    if request.method == "POST":
        barter["name"] = request.form["name"]
        barter["mobile"] = request.form["mobile"]
        barter["item"] = request.form["item"]
        barter["hostel"] = request.form["hostel"]
        return redirect(url_for("index"))

    return render_template("edit_barter.html", barter=barter)

# --- Edit Request ---
@app.route("/edit_request/<int:id>", methods=["GET", "POST"])
def edit_request(id):
    request_item = next((r for r in requests if r["id"] == id), None)
    if not request_item:
        return redirect(url_for("index"))

    if request.method == "POST":
        request_item["name"] = request.form["name"]
        request_item["mobile"] = request.form["mobile"]
        request_item["item"] = request.form["item"]
        request_item["hostel"] = request.form["hostel"]
        return redirect(url_for("index"))

    return render_template("edit_request.html", request_item=request_item)

# --- Delete Barter ---
@app.route("/delete_barter/<int:id>")
def delete_barter(id):
    global barters
    barters = [b for b in barters if b["id"] != id]
    return redirect(url_for("index"))

# --- Delete Request ---
@app.route("/delete_request/<int:id>")
def delete_request(id):
    global requests
    requests = [r for r in requests if r["id"] != id]
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets PORT
    app.run(host="0.0.0.0", port=port, debug=False)
