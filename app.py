from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# In-memory notice storage
notices = []
notice_id = 1

# --- Home Page: List + Add Form ---
@app.route("/", methods=["GET", "POST"])
def index():
    global notice_id
    if request.method == "POST":
        name = request.form["name"]
        mobile = request.form["mobile"]
        item_needed = request.form["item_needed"]
        hostel = request.form["hostel"]

        new_notice = {
            "id": notice_id,
            "name": name,
            "mobile": mobile,
            "item_needed": item_needed,
            "hostel": hostel
        }
        notices.append(new_notice)
        notice_id += 1

        return redirect(url_for("index"))

    return render_template("index.html", notices=notices)

# --- Edit Notice ---
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    notice = next((n for n in notices if n["id"] == id), None)
    if not notice:
        return redirect(url_for("index"))

    if request.method == "POST":
        notice["name"] = request.form["name"]
        notice["mobile"] = request.form["mobile"]
        notice["item_needed"] = request.form["item_needed"]
        notice["hostel"] = request.form["hostel"]
        return redirect(url_for("index"))

    return render_template("edit.html", notice=notice)

# --- Delete Notice ---
@app.route("/delete/<int:id>")
def delete(id):
    global notices
    notices = [n for n in notices if n["id"] != id]
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
