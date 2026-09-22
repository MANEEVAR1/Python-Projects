import db_connections
print("####### Welcome to Cybex Control Room #######")
print()
print("$$$$$$$ Log In to the Cybex Systems $$$$$$$")
print()
import time
admin = input("Enter Admin Password (Max 3 tries): ")
inputCount = 0
while True:
    if admin != "demo":
        inputCount += 1
        print("Invalid Admin Password")
        if inputCount == 3:
            print()
            print("Limit for Invalid Password Exceeded!")
            time.sleep(1.5)
            print("System Locked!!")
            time.sleep(2)
            print("Erasing Files.....")
            time.sleep(3)
            db_connections.cleardatabase()
            print("System Reset Successfully! All data lost.")
            break
        admin = input("Enter Admin Password (Max 3 tries): ")
    else:
        time.sleep(1.5)
        print("Access Granted!")
        print()
        time.sleep(.8)
        print("Welcome Chief")
        print()
        time.sleep(1)
        print("Select Operation to Perform in the Cybex Robot Fleet")
        # time.sleep(.5)
        print("Press 1 to add robots")
        print("Press 2 to remove robots")
        print("Press 3 to check fleet information")
        print("Press 4 to clear duplicate records")
        print("Press 5 to exit Cybex Systems")

        operation = int(input("Enter Operation to Perform: "))

        match operation:
                case 1:
                    name = input("Enter Robot Name: ")
                    ability = input("Enter Robot Ability: ")
                    db_connections.addRobots(name, ability)
                    print("Adding Robot....")
                    time.sleep(2)
                    print(f"Robot {name} added to the fleet successfully!")
                    checkFleet = input("Do you want to review the updated fleet? (y/n): ")
                    # fleetCheck = True
                    while True:
                        if checkFleet.lower() not in ("y", "n"):
                            print("Invalid Choice. Please select 'y' or 'n'")
                            checkFleet = input("Do you want to review the updated fleet? (y/n): ")
                        elif checkFleet.lower() == "n":
                            # fleetCheck = False
                            print("Exiting.....\nDone!")
                            break
                        else:
                            print("Fetching fleet details....")
                            time.sleep(1.5)
                            db_connections.getAllRobots()
                            break
                case 2:
                    name = input("Enter Robot Name: ")
                    db_connections.deleteRobots(name)
                    print("Deleting Robot....")
                    time.sleep(1)
                    print(f"Robot {name} removed from the fleet successfully!")
                    checkFleet = input("Do you want to review the updated fleet? (y/n): ")
                    while True:
                        if checkFleet.lower() not in ("y", "n"):
                            print("Invalid Choice. Please select 'y' or 'n'")
                            checkFleet = input("Do you want to review the updated fleet? (y/n): ")
                        elif checkFleet.lower() == "n":
                            print("Exiting.....\nDone!")
                            break
                        else:
                            print("Fetching fleet details....")
                            time.sleep(1.5)
                            db_connections.getAllRobots()
                            break
                case 3:
                    db_connections.getAllRobots()
                    updateRobot = input("Do you want to add/delete any robot from the fleet? (y/n): ")
                    while True:
                        if updateRobot.lower() not in ("y", "n"):
                            print("Invalid Choice. Please select 'y' or 'n'")
                            updateRobot = input("Do you want to add/delete any robot from the fleet? (y/n): ")
                        elif updateRobot.lower() == "y":
                            option = input("Press 7 to add robot & Press 13 to delete robots: ")
                            while option not in ("7", "13"):
                                print("Invalid Choice. Please select 7 or 13")
                                option = input("Press 7 to add robot & Press 13 to delete robots: ")
                            if option == "7":
                                name = input("Enter Robot Name: ")
                                ability = input("Enter Robot Ability: ")
                                print(f"Adding Robot to the fleet....")
                                time.sleep(1.5)
                                db_connections.addRobots(name, ability)
                                print(f"Robot {name} added to the fleet successfully!")
                                break
                            else:
                                name = input("Enter Robot Name: ")
                                print("Removing robot from the fleet....")
                                time.sleep(1.5)
                                db_connections.deleteRobots(name)
                                print(f"Robot {name} removed from the fleet successfully!")
                                break
                        else:
                            print("Exiting.....\nDone!")
                            break
                case 4:
                    db_connections.clearDuplicates()
                case 5:
                    db_connections.closeConnection()
                    print("Exiting Cybex Systems....\nGoodbye Chief!")
                    break
                case _:
                    print("Invalid Operation. Please select 1-5")
                    break
        break