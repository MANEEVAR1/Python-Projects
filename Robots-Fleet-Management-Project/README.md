# Cybex Control Room

A simple command-line admin panel for managing a fleet of robots, backed by a local SQLite database. Log in with an admin password, then add, remove, list, and de-duplicate robot records.

## Features

- **Password-protected login** with a maximum of 3 attempts
- **Add robots** to the fleet (name + ability)
- **Remove robots** from the fleet by name
- **View fleet information** with an inline option to add/remove robots on the spot
- **Clear duplicate records** (removes entries matching a hardcoded name)
- **Lockout safety mechanism**: after 3 failed login attempts, the database is wiped and the system resets
- **Persistent storage** via SQLite (`yourDb.db`)

## Project Structure

```
.
├── main.py            # CLI entry point / control room menu (the "Cybex Control Room" script)
├── db_connections.py  # SQLite database layer (connection, table setup, CRUD helpers)
└── yourDb.db          # SQLite database file (created automatically on first run)
```

> Rename the two scripts to match whatever you call them locally — the control room script must `import db_connections`, so the database module needs to be named `db_connections.py` and live in the same directory.

## Requirements

- Python 3.10+ (uses `match`/`case` statements)
- No external dependencies — only the standard library (`sqlite3`, `time`)

## Setup

1. Save the two scripts as `main.py` and `db_connections.py` in the same folder.
2. Run the control room:
   ```bash
   python main.py
   ```
3. On first run, `yourDb.db` and the `yourDb` table are created automatically.

## Usage

### Logging In

You'll be prompted for the admin password:

```
Enter Admin Password (Max 3 tries):
```

- Default demo password: `demo`
- ⚠️ **3 incorrect attempts will trigger `cleardatabase()`, permanently erasing all robot records.**

### Main Menu

Once logged in, choose an operation:

| Option | Action |
|--------|--------|
| 1 | Add a robot to the fleet |
| 2 | Remove a robot from the fleet |
| 3 | View fleet information (with option to add/remove inline) |
| 4 | Clear duplicate records |
| 5 | Exit Cybex Systems |

After adding or removing a robot, you'll be asked whether you want to review the updated fleet (`y`/`n`).

### Fleet Information Sub-Menu

Selecting option 3 lists all robots, then asks if you'd like to make changes:

- Press **7** to add a robot
- Press **13** to delete a robot

## Database Schema

Table: `yourDb`

| Column         | Type | Description        |
|----------------|------|---------------------|
| Name           | TEXT | Robot's name        |
| SuperAbilities | TEXT | Robot's ability/skill |

## `db_connections.py` API

| Function | Description |
|----------|-------------|
| `addRobots(name, superAbilities)` | Inserts a new robot record |
| `deleteRobots(name)` | Deletes a robot record by name |
| `getAllRobots()` | Prints all robots currently in the fleet |
| `clearDuplicates()` | Removes records where `Name = 'Alpha Beast'` |
| `cleardatabase()` | Deletes **all** records from the table |
| `closeConnection()` | Closes the SQLite connection |

## ⚠️ Known Limitations & Notes

This is a demo/learning project. Before using it for anything real, be aware of the following:

- **Plaintext password**: the admin password (`demo`) is hardcoded directly in the source. Don't reuse this for anything sensitive.
- **No SQL injection risk in current queries** — parameterized queries are used correctly for inserts/deletes, but `clearDuplicates()` hardcodes the target name (`Alpha Beast`) rather than accepting input.
- **`deleteRobots` column case mismatch**: the query uses `WHERE name = ?` (lowercase `name`), while the table column is defined as `Name` (capital `N`). SQLite is case-insensitive for column names by default, so this works, but for consistency consider matching case.
- **Menu exits after one operation**: the `break` at the end of the main loop means the menu is only shown once per successful login; you'll need to restart the program to perform another top-level operation after finishing one (unless you use the sub-menus inside options 1–3).
- **No input validation on `operation`**: entering a non-integer at the "Enter Operation to Perform" prompt will raise an unhandled `ValueError` and crash the program.
- **Destructive lockout**: the 3-strikes password lockout deletes the entire database. There's no confirmation step or backup — use with caution, especially during testing.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).