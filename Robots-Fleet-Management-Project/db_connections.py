import sqlite3
connection = sqlite3.connect("yourDb.db")
cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS yourDb (Name TEXT, SuperAbilities TEXT)""")
connection.commit()

connection.commit()

cursor.execute("SELECT * FROM yourDb")

def addRobots(name, superAbilities):
    cursor.execute("INSERT INTO yourDb VALUES (?, ?)", (name, superAbilities))
    connection.commit()

def deleteRobots(name):
    cursor.execute("DELETE FROM yourDb WHERE name = ?", (name, ))
    connection.commit()

def getAllRobots():
    import time
    cursor.execute("SELECT * FROM yourDb")
    results = cursor.fetchall()
    print("Fetching all robots data from the database....")
    time.sleep(2)
    if not results:
        print("Fleet is currently empty")
    else:
        for robot in results:
            print(f"{robot[0]}:\n{robot[1]}")

def clearDuplicates():
    cursor.execute("DELETE FROM yourDb where Name = 'Alpha Beast'")
    connection.commit()

def cleardatabase():
    cursor.execute("DELETE FROM yourDb")
    connection.commit()

def closeConnection():
    connection.close()