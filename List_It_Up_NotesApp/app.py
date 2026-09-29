from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras
import time
import random
import os

app = Flask(__name__)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            "userId" INTEGER PRIMARY KEY,
            "userName" TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_notes (
            "notesId" INTEGER PRIMARY KEY,
            notes TEXT,
            timestamp TEXT,
            "userId" INTEGER,
            FOREIGN KEY ("userId") REFERENCES users("userId")
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/create', methods=['POST'])
def create_note():
    data = request.json
    userId   = data.get('userId')
    userName = data.get('userName', '').strip()
    notes    = data.get('notes', '').strip()

    if not userId or not userName or not notes:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    try:
        userId = int(userId)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'User ID must be a number.'}), 400

    timestamp = time.strftime("%B %d, %Y — %I:%M %p")

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # Check if userId already exists with a DIFFERENT userName
        cursor.execute('SELECT "userName" FROM users WHERE "userId" = %s', (userId,))
        existing_user = cursor.fetchone()
        if existing_user and existing_user[0] != userName:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': f'User ID {userId} belongs to "{existing_user[0]}", not "{userName}".'}), 409

        # Check if userName already exists with a DIFFERENT userId
        cursor.execute('SELECT "userId" FROM users WHERE "userName" = %s', (userName,))
        existing_name = cursor.fetchone()
        if existing_name and existing_name[0] != userId:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': f'Username "{userName}" is already taken by another user.'}), 409

        # Safe to insert/ignore user
        cursor.execute("""
            INSERT INTO users ("userId", "userName")
            VALUES (%s, %s)
            ON CONFLICT ("userId") DO NOTHING
        """, (userId, userName))

        # Generate a unique notesId (retry on collision)
        for _ in range(5):
            notesId = random.randint(1, 9999999)
            cursor.execute('SELECT "notesId" FROM users_notes WHERE "notesId" = %s', (notesId,))
            if cursor.fetchone() is None:
                break

        cursor.execute(
            'INSERT INTO users_notes ("notesId", notes, timestamp, "userId") VALUES (%s, %s, %s, %s)',
            (notesId, notes, timestamp, userId)
        )
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Note created successfully.', 'notesId': notesId, 'timestamp': timestamp})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/read/<int:notesId>', methods=['GET'])
def read_note(notesId):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n."notesId", n.notes, n.timestamp, u."userName"
            FROM users_notes n
            JOIN users u ON n."userId" = u."userId"
            WHERE n."notesId" = %s
        """, (notesId,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        if row is None:
            return jsonify({'success': False, 'message': f'No note found with ID #{notesId}.'}), 404
        return jsonify({'success': True, 'note': {'id': row[0], 'content': row[1], 'timestamp': row[2], 'author': row[3]}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/update/<int:notesId>', methods=['PUT'])
def update_note(notesId):
    data  = request.json
    notes = data.get('notes', '').strip()
    if not notes:
        return jsonify({'success': False, 'message': 'Note content is required.'}), 400
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT "notesId" FROM users_notes WHERE "notesId" = %s', (notesId,))
        if cursor.fetchone() is None:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': f'No note found with ID #{notesId}.'}), 404
        timestamp = time.strftime("%B %d, %Y — %I:%M %p")
        cursor.execute(
            'UPDATE users_notes SET notes = %s, timestamp = %s WHERE "notesId" = %s',
            (notes, timestamp, notesId)
        )
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Note updated successfully.', 'timestamp': timestamp})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete/<int:notesId>', methods=['DELETE'])
def delete_note(notesId):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT "notesId" FROM users_notes WHERE "notesId" = %s', (notesId,))
        if cursor.fetchone() is None:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': f'No note found with ID #{notesId}.'}), 404
        cursor.execute('DELETE FROM users_notes WHERE "notesId" = %s', (notesId,))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Note deleted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/notes/<string:userName>', methods=['GET'])
def see_all_notes(userName):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT "userId" FROM users WHERE "userName" = %s', (userName,))
        user = cursor.fetchone()
        if user is None:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': f'User "{userName}" does not exist.'}), 404
        cursor.execute(
            'SELECT "notesId", notes, timestamp FROM users_notes WHERE "userId" = %s ORDER BY "notesId" DESC',
            (user[0],)
        )
        rows  = cursor.fetchall()
        cursor.close(); conn.close()
        notes = [{'id': r[0], 'content': r[1], 'timestamp': r[2]} for r in rows]
        return jsonify({'success': True, 'notes': notes, 'userName': userName})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/deleteall/<int:userId>', methods=['DELETE'])
def delete_all_notes(userId):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT "notesId" FROM users_notes WHERE "userId" = %s', (userId,))
        rows = cursor.fetchall()
        if not rows:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': f'No notes found for User ID {userId}.'}), 404
        cursor.execute('DELETE FROM users_notes WHERE "userId" = %s', (userId,))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': f'All {len(rows)} notes deleted successfully.', 'count': len(rows)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)