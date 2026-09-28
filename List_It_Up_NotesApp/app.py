from flask import Flask, render_template, request, jsonify
import Notes_db
import time
import random

app = Flask(__name__)
app.secret_key = "list-it-up-secret-key-change-in-prod"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.get_json() or {}
    user_id = data.get("userId")
    user_name = data.get("userName", "").strip()
    notes = data.get("notes", "").strip()

    if not str(user_id).isdigit():
        return jsonify({"success": False, "message": "User ID must be a number."}), 400
    if not user_name:
        return jsonify({"success": False, "message": "Username is required."}), 400
    if not notes:
        return jsonify({"success": False, "message": "Note content cannot be empty."}), 400

    notes_id = random.randint(1000, 999999)
    timestamp = time.ctime()
    result = Notes_db_sourceCode.create_note(int(user_id), user_name, notes_id, notes, timestamp)
    return jsonify(result)

@app.route("/api/read", methods=["POST"])
def api_read():
    data = request.get_json() or {}
    notes_id = data.get("notesId")
    if not str(notes_id).isdigit():
        return jsonify({"success": False, "message": "Note ID must be a number."}), 400
    result = Notes_db_sourceCode.read_note(int(notes_id))
    return jsonify(result)

@app.route("/api/update", methods=["POST"])
def api_update():
    data = request.get_json() or {}
    notes_id = data.get("notesId")
    notes = data.get("notes", "").strip()
    if not str(notes_id).isdigit():
        return jsonify({"success": False, "message": "Note ID must be a number."}), 400
    if not notes:
        return jsonify({"success": False, "message": "Updated note content cannot be empty."}), 400
    result = Notes_db_sourceCode.update_note(int(notes_id), notes)
    return jsonify(result)

@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = request.get_json() or {}
    notes_id = data.get("notesId")
    if not str(notes_id).isdigit():
        return jsonify({"success": False, "message": "Note ID must be a number."}), 400
    result = Notes_db_sourceCode.delete_note(int(notes_id))
    return jsonify(result)

@app.route("/api/all", methods=["POST"])
def api_all():
    data = request.get_json() or {}
    user_name = data.get("userName", "").strip()
    if not user_name:
        return jsonify({"success": False, "message": "Username is required."}), 400
    if user_name.isdigit():
        return jsonify({"success": False, "message": "Username must be text, not only numbers."}), 400
    result = Notes_db_sourceCode.see_all_notes(user_name)
    return jsonify(result)

@app.route("/api/delete-all", methods=["POST"])
def api_delete_all():
    data = request.get_json() or {}
    user_id = data.get("userId")
    if not str(user_id).isdigit():
        return jsonify({"success": False, "message": "User ID must be a number."}), 400
    result = Notes_db_sourceCode.delete_all_notes(int(user_id))
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)