import socket
import sqlite3
import sys
import threading

running = True                                                  #SHUTDOWN command turns running to false
accepted = "200 OK"                                             #string to send to client if command works
db = sqlite3.connect("crypto.sqlite", check_same_thread=False)  #connection to database
cur = db.cursor()                                               #used to do sql queries
port = 9179                                                     #initiate port


#used to check if variables can be turned to floats
def is_float(num):
    try:
        float(num)
        return True
    except:
        return False


def handle_client(conn, address):
    loggedIn = False;
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print(f"Connection from: {ip_address}")
    global running
    global accepted

    #connect to client and receive commands
    while running:
        try:
            data = conn.recv(1024).decode()
        except:
            break           #breaks when data is not defined
            
        if not data:
            break

        print(f"Recieved from {ip_address}: {str(data)}")

        #splits user string into workable data
        userStatement = data.split(" ")
        command = userStatement[0]

        #LOGIN COMMAND
        #takes the username and password from arguments and checks the db for an existing user, if so, admit them.
        if command == "LOGIN":
            if len(userStatement) < 3: #checks for proper formatting and values for the BUY command
                conn.send("403 message format error".encode())
                continue
            username = userStatement[1]
            password = userStatement[2]
            result = cur.execute("SELECT ID FROM USERS WHERE user_name = '" + username + "' AND password = '" + password + "'")
            temp = result.fetchone()
            if temp is None:
                conn.send("403 Wrong UserID or Password".encode())
                continue
            userID = temp[0]
            
            #user is now logged in
            if userID != 0:
                loggedIn = True
                conn.send(accepted.encode())
                #storing logged_in state and last connected ip within database
                cur.execute("UPDATE USERS SET logged_in = '" + str(1) + "' WHERE user_name = '" + username + "'")
                db.commit()
                cur.execute("UPDATE USERS SET last_ip = '" + str(ip_address) + "' WHERE user_name = '" + username + "'")
                db.commit()
        
        elif command == "QUIT":
            conn.send("Quitting client...".encode())

        else:
            conn.send("400 invalid command".encode())

        #MAIN COMMAND LOOP UNTIL USER LOGS OUT
        while loggedIn:
            try:
                data = conn.recv(1024).decode()
            except:
                break
            
            if not data:
                break
            print("Recieved: " + str(data))
            userStatement = data.split(" ")
            if len(userStatement) < 1:
                continue
            command = userStatement[0]

            #if command is formatted correctly, BUY selects the current balance of the crypto
            #if it exists and user has enough money, update the current crypto
            #if it doesn't exist and user has enough money, insert a new crypto
            #at the end, send a confirmation of new balances to user
            if command == "BUY":
                userbal = 0.0
                if len(userStatement) < 4: #checks for proper formatting and values for the BUY command
                    conn.send("403 message format error".encode())
                    continue
                if not (is_float(userStatement[2]) and is_float(userStatement[3])):
                    conn.send("403 message format error".encode())
                    continue
                cryptoName = userStatement[1]
                amount = float(userStatement[2])
                price = float(userStatement[3])
                result = cur.execute("SELECT usd_balance FROM USERS WHERE user_name = '" + username + "'")
                temp = result.fetchone()
                if temp is None:
                    conn.send("User not found".encode())
                    continue
                
                userbal = temp[0]    
                userbal = float(userbal - (amount * price)) #update balance value
                if userbal < 0:
                    conn.send("Not enough balance".encode())
                    continue
                result = cur.execute("SELECT crypto_balance FROM CRYPTOS WHERE crypto_name = '" + cryptoName + "' AND user_id = '" + username + "'")
                temp = result.fetchone()
                if temp is None:
                    cur.execute("INSERT INTO CRYPTOS (crypto_name, crypto_balance, user_id) VALUES ('" + cryptoName + "','" + str(amount) +"','" + username + "')") #if no crypto found, insert one
                    db.commit()
                else:
                    oldAmount = temp[0]
                    amount += oldAmount
                    cur.execute("UPDATE CRYPTOS SET crypto_balance = '" + str(amount) + "' WHERE user_id = '" + username + "' AND crypto_name = '" + cryptoName + "'")
                    db.commit()
                cur.execute("UPDATE USERS SET usd_balance = '" + str(userbal) + "' WHERE user_name = '" + username + "'") #update balance in users account
                db.commit()
                result = cur.execute("SELECT crypto_balance FROM CRYPTOS WHERE crypto_name = '" + cryptoName + "' AND user_id = '" + username + "'")
                cryptoBal = result.fetchone()[0]
                confirm = accepted +"\nBOUGHT: New balance: %.2f %s USD Balance: $%.2f" % (amount,cryptoName, userbal)
                conn.send(confirm.encode())

            #if command is formatted correctly, SELL selects the current balance of the crypto
            #if crypto is found and there is enough balance, sell the crypto
            #update the balance of the crypto and the users balance
            #at the end, send a confirmation of new balances to user
            elif command == "SELL":
                userbal = 0.0
                oldAmount = 0.0
                if len(userStatement) < 4: #checks for proper formatting and values for the SELL command
                    conn.send("403 message format error".encode())
                    continue
                if not (is_float(userStatement[2]) and is_float(userStatement[3])):
                    conn.send("403 message format error".encode())
                    continue
                cryptoName = userStatement[1]
                amount = float(userStatement[2])
                price = float(userStatement[3])
                result = cur.execute("SELECT usd_balance FROM USERS WHERE user_name = '" + username + "'")
                temp = result.fetchone()
                if temp is None:
                    conn.send("User not found".encode())
                    continue
                else:
                    userbal = temp[0]
                result = cur.execute("SELECT crypto_balance FROM CRYPTOS WHERE crypto_name = '" + cryptoName + "' AND user_id = '" + username + "'")
                temp = result.fetchone()
                if temp is None:
                    conn.send("Crypto not found".encode())
                    continue
                else:
                    oldAmount = temp[0]
                
                userbal += float(amount * price)
                amount = oldAmount - amount
                
                if amount < 0:
                    conn.send("Not enough crypto".encode())
                    continue
                cur.execute("UPDATE CRYPTOS SET crypto_balance = '" + str(amount) + "' WHERE user_id = '" + username + "' AND crypto_name = '" + cryptoName + "'")
                db.commit()
                cur.execute("UPDATE USERS SET usd_balance = '" + str(userbal) + "' WHERE user_name = '" + username + "'") #update balance in users account
                db.commit()
                confirm = accepted +"\nSOLD: New balance: %.2f %s USD Balance: $%.2f" % (amount,cryptoName, userbal)
                conn.send(confirm.encode())

            #for LIST, all the cryptos in the crypto table is selected
            #for each crypto in the database, a new line is added to the string to be sent
            #when there are no more cryptos to add to string, send the message to the user
            elif command == "LIST":
                if username == "root":
                    message = accepted +"\nThe list of records in the Crypto database for ALL users:\n"
                    result = cur.execute("SELECT ID, crypto_name, crypto_balance, user_id FROM CRYPTOS")
                    cryptoVals = result.fetchone()
                    while cryptoVals is not None:
                        
                        message += str(cryptoVals[0]) + " " + cryptoVals[1] + " " + str(cryptoVals[2]) + " " + cryptoVals[3] +"\n"
                        cryptoVals = result.fetchone()
                    
                    conn.send(message.encode())

                else:
                    message = accepted + "\nThe list of records in the Crypto database for " + username + ":\n"
                    result = cur.execute("SELECT ID, crypto_name, crypto_balance FROM CRYPTOS WHERE user_id = '" + username + "'")
                    cryptoVals = result.fetchone()
                    while cryptoVals is not None:
                        
                        message += str(cryptoVals[0]) + " " + cryptoVals[1] + " " + str(cryptoVals[2]) + "\n"
                        cryptoVals = result.fetchone()
                    
                    conn.send(message.encode())

            elif command == "BALANCE":
                result = cur.execute("SELECT first_name, last_name, usd_balance FROM USERS WHERE user_name = '" + username + "'")
                userInfo = result.fetchone()

                confirm = accepted +"\nBalance for user " + userInfo[0] + " " + userInfo[1] + ": $" + str(userInfo[2])
                conn.send(confirm.encode())

            elif command == "WHO":
                if username == "root":
                    message = accepted +"\nThe list of the active users:"
                    result = cur.execute("SELECT user_name, last_ip FROM USERS WHERE logged_in = '1'")
                    activeUsers = result.fetchone()

                    while activeUsers is not None:
                        message += "\n" + str(activeUsers[0]) + " " + activeUsers[1]
                        activeUsers = result.fetchone()

                    conn.send(message.encode())
                
                else:
                    conn.send("Need root user permissions".encode())

            elif command == "DEPOSIT":

                if len(userStatement) < 2: #checks for proper formatting and values for the SELL command
                    conn.send("403 message format error".encode())
                    continue
                if not (is_float(userStatement[1]) and float(userStatement[1]) > 0):
                    conn.send("403 invalid input for $ amount".encode())
                    continue

                result = cur.execute("SELECT usd_balance FROM USERS WHERE user_name = '" + username + "'")
                temp = result.fetchone()
                currentBalance = float(temp[0])
                newBalance = currentBalance + float(userStatement[1])
                cur.execute("UPDATE USERS SET usd_balance = '" + str(newBalance) + "' WHERE user_name = '" + username + "'")
                db.commit()

                result = cur.execute("SELECT usd_balance FROM USERS WHERE user_name = '" + username + "'")
                userInfo = result.fetchone()
                userbal = float(userInfo[0])
                confirm = accepted +"\nDeposit successful. New balance: $%.2f" % (userbal)
                conn.send(confirm.encode())

            elif command == "LOOKUP":
                if len(userStatement) < 2: #checks for proper formatting and values for the LOOKUP command
                    conn.send("403 message format error".encode())
                    continue

                cryptoName = userStatement[1]
                matchedCryptos = 0

                message = accepted + "\n"
                result = cur.execute("SELECT crypto_name, crypto_balance FROM CRYPTOS WHERE user_id = '" + username + "' AND crypto_name = '" + cryptoName + "'")
                userCrypto = result.fetchone()
                
                while userCrypto is not None:
                    matchedCryptos += 1
                    message += str(userCrypto[0]) + " " + str(userCrypto[1]) + "\n"
                    userCrypto = result.fetchone()
                matchedMessage = "Found " + str(matchedCryptos) + " matching records\n"
                conn.send((matchedMessage + message).encode())


            elif command == "LOGOUT":
                loggedIn = False
                cur.execute("UPDATE USERS SET logged_in = '" + str(0) + "' WHERE user_name = '" + username + "'")
                db.commit()
                del username
                conn.send(accepted.encode())

            #for shutdown, set condition for outer loop to false
            #this will stop the server from looping and closes the server
            elif command == "QUIT":
                loggedIn = False
                cur.execute("UPDATE USERS SET logged_in = '" + str(0) + "' WHERE user_name = '" + username + "'")
                db.commit()
                conn.send("Closing client...".encode())
                break

            elif command == "SHUTDOWN":
                loggedIn = False
                running = False
                cur.execute("UPDATE USERS SET logged_in = '" + str(0) + "' WHERE user_name = '" + username + "'")
                db.commit()
                conn.send("Shutting down server...".encode())
                break

            else:
                error = "400 invalid command"
                conn.send(error.encode())
  
    conn.close()

def server_program():
    #if proper command line formatting is done, host is set to the ip entered
    #if command line formatting done wrong, code exits
    host = ""
    n = len(sys.argv)
    if n == 2:
        host = sys.argv[1]
        print(host)
    elif n == 1:
        host = socket.gethostbyname(socket.gethostname())
    else:
        print("Invalid number of arguments")
        return 0
    

    server_socket = socket.socket()  # get instance
    server_socket.bind((host, port))  # bind host address and port together
    server_socket.listen(3)
    
#creates the users table
    cur.execute("""
CREATE TABLE IF NOT EXISTS "users" (
	"ID"	INTEGER,
	"email"	TXT NOT NULL,
	"first_name"	TEXT,
	"last_name"	TEXT,
	"user_name"	TEXT NOT NULL,
	"password"	TEXT,
	"usd_balance"	DOUBLE NOT NULL,
    "logged_in" INTEGER,
    "last_ip"   TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT)
);
    """)

#creates the cryptos table
    cur.execute("""
CREATE TABLE IF NOT EXISTS "cryptos" (
	"ID"	INTEGER,
	"crypto_name"	varchar(10) NOT NULL,
	"crypto_balance"	DOUBLE,
	"user_id"	TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "users"("user_name")
);
    """)

    #checks if a user exists
    #if value is null there is no users and one must be created
    result = cur.execute("SELECT usd_balance FROM USERS WHERE ID = 1")
    if result.fetchone() is None:
        cur.execute("INSERT INTO USERS (email, first_name, last_name, user_name, password, usd_balance) VALUES ('rootuser@example.com', 'Root', 'User', 'root', 'root01', 100)")
        cur.execute("INSERT INTO USERS (email, first_name, last_name, user_name, password, usd_balance) VALUES ('marybeth@example.com', 'Mary', 'Beth', 'mary', 'mary01', 100)")
        cur.execute("INSERT INTO USERS (email, first_name, last_name, user_name, password, usd_balance) VALUES ('johnappleseed@example.com', 'John', 'Appleseed', 'john', 'john01', 100)")
        cur.execute("INSERT INTO USERS (email, first_name, last_name, user_name, password, usd_balance) VALUES ('moesyed@example.com', 'Moe', 'Syed', 'moe', 'moe01', 100)")
        db.commit()

    global running
    
    while running:
        server_socket.settimeout(10)
        try:
            conn, address = server_socket.accept()  # accept new connection, in loop incase client disconnects
            client_thread = threading.Thread(target=handle_client, args=(conn, address))
            client_thread.start()
        except:
            print("10 Second timeout")
        
    db.close() #close the database
    server_socket.close()

if __name__ == '__main__':
    server_program()