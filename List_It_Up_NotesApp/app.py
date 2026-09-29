from flask import Flask, request, jsonify, render_template
import os
import random
import time

import psycopg2


app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    "userId" INTEGER PRIMARY KEY,
                    "userName" TEXT UNIQUE NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users_notes (
                    "notesId" INTEGER PRIMARY KEY,
                    notes TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    "userId" INTEGER NOT NULL,
                    FOREIGN KEY ("userId") REFERENCES users("userId")
                )
            """)
        conn.commit()
    finally:
        conn.close()


init_db()


def error_response(message, status=500):
    return jsonify({"success": False, "message": message}), status


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/create", methods=["POST"])
def create_note():
    data = request.get_json(silent=True) or {}

    user_id = data.get("userId")
    user_name = str(data.get("userName", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if user_id in (None, "") or not user_name or not notes:
        return error_response("All fields are required.", 400)

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return error_response("User ID must be a number.", 400)

    if user_id <= 0:
        return error_response("User ID must be a positive number.", 400)

    timestamp = time.strftime("%B %d, %Y — %I:%M %p")
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            # Keep the userId <-> userName relationship consistent.
            cursor.execute(
                'SELECT "userName" FROM users WHERE "userId" = %s',
                (user_id,)
            )
            existing_user = cursor.fetchone()

            if existing_user and existing_user[0] != user_name:
                conn.rollback()
                return error_response(
                    f'User ID {user_id} belongs to "{existing_user[0]}", not "{user_name}".',
                    409
                )

            cursor.execute(
                'SELECT "userId" FROM users WHERE "userName" = %s',
                (user_name,)
            )
            existing_name = cursor.fetchone()

            if existing_name and existing_name[0] != user_id:
                conn.rollback()
                return error_response(
                    f'Username "{user_name}" is already taken by another user.',
                    409
                )

            cursor.execute("""
                INSERT INTO users ("userId", "userName")
                VALUES (%s, %s)
                ON CONFLICT ("userId") DO NOTHING
            """, (user_id, user_name))

            # Generate and insert the ID atomically. This avoids the
            # check-then-insert race of SELECT-then-INSERT.
            notes_id = None

            for _ in range(20):
                candidate = random.randint(1, 9_999_999)
                cursor.execute("""
                    INSERT INTO users_notes
                        ("notesId", notes, timestamp, "userId")
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT ("notesId") DO NOTHING
                    RETURNING "notesId"
                """, (candidate, notes, timestamp, user_id))

                inserted = cursor.fetchone()
                if inserted is not None:
                    notes_id = inserted[0]
                    break

            if notes_id is None:
                conn.rollback()
                return error_response(
                    "Could not generate a unique Note ID. Please try again.",
                    503
                )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Note created successfully.",
            "notesId": notes_id,
            "timestamp": timestamp
        })

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return error_response("Database error while creating the note.", 500)

    except Exception:
        if conn:
            conn.rollback()
        return error_response("Unexpected server error.", 500)

    finally:
        if conn:
            conn.close()


@app.route("/api/read/<int:notesId>", methods=["GET"])
def read_note(notesId):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    n."notesId",
                    n.notes,
                    n.timestamp,
                    u."userName"
                FROM users_notes n
                JOIN users u
                  ON n."userId" = u."userId"
                WHERE n."notesId" = %s
            """, (notesId,))

            row = cursor.fetchone()

        if row is None:
            return error_response(
                f"No note found with ID #{notesId}.",
                404
            )

        return jsonify({
            "success": True,
            "note": {
                "id": row[0],
                "content": row[1],
                "timestamp": row[2],
                "author": row[3]
            }
        })

    except psycopg2.Error:
        return error_response("Database error while reading the note.", 500)

    except Exception:
        return error_response("Unexpected server error.", 500)

    finally:
        if conn:
            conn.close()


@app.route("/api/update/<int:notesId>", methods=["PUT"])
def update_note(notesId):
    data = request.get_json(silent=True) or {}
    notes = str(data.get("notes", "")).strip()

    if not notes:
        return error_response("Note content is required.", 400)

    timestamp = time.strftime("%B %d, %Y — %I:%M %p")
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE users_notes
                SET notes = %s, timestamp = %s
                WHERE "notesId" = %s
                RETURNING "notesId"
            """, (notes, timestamp, notesId))

            updated = cursor.fetchone()

            if updated is None:
                conn.rollback()
                return error_response(
                    f"No note found with ID #{notesId}.",
                    404
                )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Note updated successfully.",
            "timestamp": timestamp
        })

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return error_response("Database error while updating the note.", 500)

    except Exception:
        if conn:
            conn.rollback()
        return error_response("Unexpected server error.", 500)

    finally:
        if conn:
            conn.close()


@app.route("/api/delete/<int:notesId>", methods=["DELETE"])
def delete_note(notesId):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            # RETURNING makes the operation atomic:
            # no separate SELECT + DELETE race.
            cursor.execute("""
                DELETE FROM users_notes
                WHERE "notesId" = %s
                RETURNING "notesId"
            """, (notesId,))

            deleted = cursor.fetchone()

            if deleted is None:
                conn.rollback()
                return error_response(
                    f"No note found with ID #{notesId}.",
                    404
                )

        conn.commit()

        return jsonify({
            "success": True,
            "message": f"Note #{notesId} deleted successfully."
        })

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return error_response("Database error while deleting the note.", 500)

    except Exception:
        if conn:
            conn.rollback()
        return error_response("Unexpected server error.", 500)

    finally:
        if conn:
            conn.close()


@app.route("/api/notes/<string:userName>", methods=["GET"])
def see_all_notes(userName):
    user_name = userName.strip()

    if not user_name:
        return error_response("Username is required.", 400)

    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT "userId" FROM users WHERE "userName" = %s',
                (user_name,)
            )
            user = cursor.fetchone()

            if user is None:
                return error_response(
                    f'User "{user_name}" does not exist.',
                    404
                )

            cursor.execute("""
                SELECT "notesId", notes, timestamp
                FROM users_notes
                WHERE "userId" = %s
                ORDER BY "notesId" DESC
            """, (user[0],))

            rows = cursor.fetchall()

        notes = [
            {
                "id": row[0],
                "content": row[1],
                "timestamp": row[2]
            }
            for row in rows
        ]

        return jsonify({
            "success": True,
            "notes": notes,
            "userName": user_name
        })

    except psycopg2.Error:
        return error_response("Database error while loading notes.", 500)

    except Exception:
        return error_response("Unexpected server error.", 500)

    finally:
        if conn:
            conn.close()


@app.route("/api/deleteall/<int:userId>", methods=["DELETE"])
def delete_all_notes(userId):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM users_notes
                WHERE "userId" = %s
                RETURNING "notesId"
            """, (userId,))

            deleted_rows = cursor.fetchall()

            if not deleted_rows:
                conn.rollback()
                return error_response(
                    f"No notes found for User ID {userId}.",
                    404
                )

        conn.commit()

        count = len(deleted_rows)

        return jsonify({
            "success": True,
            "message": f"All {count} notes deleted successfully.",
            "count": count
        })

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return error_response("Database error while deleting notes.", 500)

    except Exception:
        if conn:
            conn.rollback()
        return error_response("Unexpected server error.", 500)

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
