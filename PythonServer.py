import socket
import sqlite3
import sys
import threading

running = True #shutdown function turns running to false
accepted = "200 OK" #string to send to client if command works
db = sqlite3.connect("crypto.sqlite", check_same_thread=False) #connection to database
cur = db.cursor() #used to do sql queries

#used to check if variables can be turned to floats
def is_float(f):
    try:
        float(f)
        return True
    except:
        return False



def handle_client(conn, address):
    loggedIn = False;
    print("Connection from: " + str(address))
    global running
    global accepted
    while running:
        try:
            data = conn.recv(1024).decode()
        except:
            break
            
        if not data:
            break
        print("s: Recieved: " + str(data))
        userStatement = data.split(" ")
        command = userStatement[0]

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
            
            if userID != 0:
                loggedIn = True
                conn.send(accepted.encode())
        else:
            conn.send("400 invalid command".encode())
        while loggedIn:
            try:
                data = conn.recv(1024).decode()
            except:
                break
            
            if not data:
                break
            print("s: Recieved: " + str(data))
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
                if len(userStatement) < 5: #checks for proper formatting and values for the BUY command
                    conn.send("403 message format error".encode())
                    continue
                if not (is_float(userStatement[2]) and is_float(userStatement[3]) and userStatement[4].isdigit()):
                    conn.send("403 message format error".encode())
                    continue
                cryptoName = userStatement[1]
                userID = userStatement[4]
                amount = float(userStatement[2])
                price = float(userStatement[3])
                result = cur.execute("SELECT usd_balance FROM USERS WHERE ID = " + userID)
                temp = result.fetchone()
                if temp is None:
                    conn.send("User not found".encode())
                    continue
                
                userbal = temp[0]    
                userbal = float(userbal - (amount * price)) #update balance value
                if userbal < 0:
                    conn.send("Not enough balance".encode())
                    continue
                result = cur.execute("SELECT crypto_balance FROM CRYPTOS WHERE crypto_name = '" + cryptoName + "' AND user_id = '" + userID + "'")
                temp = result.fetchone()
                if temp is None:
                    cur.execute("INSERT INTO CRYPTOS (crypto_name, crypto_balance, user_id) VALUES ('" + cryptoName + "','" + str(amount) +"','" + userID + "')") #if no crypto found, insert one
                    db.commit()
                else:
                    oldAmount = temp[0]
                    amount += oldAmount
                    cur.execute("UPDATE CRYPTOS SET crypto_balance = '" + str(amount) + "' WHERE user_id = '" + userID + "' AND crypto_name = '" + cryptoName + "'")
                    db.commit()
                cur.execute("UPDATE USERS SET usd_balance = '" + str(userbal) + "' WHERE ID = '" + userID + "'") #update balance in users account
                db.commit()
                result = cur.execute("SELECT crypto_balance FROM CRYPTOS WHERE crypto_name = '" + cryptoName + "' AND user_id = '" + userID + "'")
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
                if len(userStatement) < 5: #checks for proper formatting and values for the SELL command
                    conn.send("403 message format error".encode())
                    continue
                if not (is_float(userStatement[2]) and is_float(userStatement[3]) and userStatement[4].isdigit()):
                    conn.send("403 message format error".encode())
                    continue
                cryptoName = userStatement[1]
                userID = userStatement[4]
                amount = float(userStatement[2])
                price = float(userStatement[3])
                result = cur.execute("SELECT usd_balance FROM USERS WHERE ID = '" + userID + "'")
                temp = result.fetchone()
                if temp is None:
                    conn.send("User not found".encode())
                    continue
                else:
                    userbal = temp[0]
                result = cur.execute("SELECT crypto_balance FROM CRYPTOS WHERE crypto_name = '" + cryptoName + "' AND user_id = '" + userID + "'")
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
                cur.execute("UPDATE CRYPTOS SET crypto_balance = '" + str(amount) + "' WHERE user_id = '" + userID + "' AND crypto_name = '" + cryptoName + "'")
                db.commit()
                cur.execute("UPDATE USERS SET usd_balance = '" + str(userbal) + "' WHERE ID = '" + userID + "'") #update balance in users account
                db.commit()
                confirm = accepted +"\nSOLD: New balance: %.2f %s USD Balance: $%.2f" % (amount,cryptoName, userbal)
                conn.send(confirm.encode())

            #for LIST, all the cryptos in the crypto table is selected
            #for each crypto in the database, a new line is added to the string to be sent
            #when there are no more cryptos to add to string, send the message to the user
            elif command == "LIST":
                message = accepted +"\nThe list of records in the Crypto database for user 1:\n"
                result = cur.execute("SELECT ID, crypto_name, crypto_balance FROM CRYPTOS WHERE user_id = '1'")
                cryptoVals = result.fetchone()
                while cryptoVals is not None:
                    
                    message += str(cryptoVals[0]) + " " + cryptoVals[1] + " " + str(cryptoVals[2]) + "\n"
                    cryptoVals = result.fetchone()
                
                conn.send(message.encode())
            elif command == "BALANCE":
                result = cur.execute("SELECT first_name, last_name, usd_balance FROM USERS")
                userInfo = result.fetchone()

                confirm = accepted +"\nBalance for user " + userInfo[0] + " " + userInfo[1] + ": $" + str(userInfo[2])
                conn.send(confirm.encode())

            #for shutdown, set condition for outer loop to false
            #this will stop the server from looping and closes the server
            elif command == "SHUTDOWN":
                loggedIn = False
                running = False
                break
            elif command == "LOGOUT":
                loggedIn = False
                conn.send(accepted.encode())
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



    

    
    
    port = 9179  # initiate port

    server_socket = socket.socket()  # get instance
    server_socket.bind((host, port))  # bind host address and port together

    server_socket.listen(3)
    
    
    cur.execute("""
CREATE TABLE IF NOT EXISTS "users" (
	"ID"	INTEGER,
	"email"	TXT NOT NULL,
	"first_name"	TEXT,
	"last_name"	TEXT,
	"user_name"	TEXT NOT NULL,
	"password"	TEXT,
	"usd_balance"	DOUBLE NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
);
    """)
    cur.execute("""
    
CREATE TABLE IF NOT EXISTS "cryptos" (
	"ID"	INTEGER,
	"crypto_name"	varchar(10) NOT NULL,
	"crypto_balance"	DOUBLE,
	"user_id"	TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "users"("ID")
);
    """)

    #checks if a user exists
    #if value is null there is no users and one must be created
    result = cur.execute("SELECT usd_balance FROM USERS WHERE ID = 1")
    if result.fetchone() is None:
        cur.execute("INSERT INTO USERS (email, first_name, last_name, user_name, password, usd_balance) VALUES ('email@example.com', 'Moe', 'Syed', 'msyed', 'password123', 100)")
    global running
    while running:
        server_socket.settimeout(10)
        
        try:
            conn, address = server_socket.accept()  # accept new connection, in loop incase client disconnects
            client_thread = threading.Thread(target=handle_client, args=(conn, address))
            client_thread.start()
        except:
            print("IDK")
        
    db.close() #close the database
    server_socket.close()

if __name__ == '__main__':
    server_program()