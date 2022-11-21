# Project 2 by Jonathan Schall and Greg Kosakowski
# CIS 427
# 11/13/2022

import socket
import sys

PORT = 5425  # socket server port number

# in case of python 2
try:
    input = raw_input
except NameError:
    pass


def client_program():
    # if proper command line formatting is done, host is set to the ip entered
    # if command line formatting done wrong, code exits
    host = ""
    n = len(sys.argv)
    if n == 2:
        print(sys.argv[1])
        host = sys.argv[1]
    else:
        print("Invalid number of arguments")
        return

    client_socket = socket.socket()  

    # connects to the server, if cannot code exits
    try:
         client_socket.connect((host, PORT))  
    except:
        print("500 cannot connect to server")
        return

    quitFlag = 0        # flag that breaks out of while loop when user command = quit
    shutdownFlag = 0    # flag that breaks out of while loop when user command = shutdown

    while quitFlag == 0 and shutdownFlag == 0:

        message = input("\nc: ")  # take input
        
        if message.lower().strip() == "quit":
            quitFlag = 1
            
        if len(message) > 0:
            try:
                client_socket.send(message.encode())        # send message
                data = client_socket.recv(1024).decode()    # receive response
                if data == "Shutting down server...":
                    shutdownFlag = 1
                print("s: " + data)                         # show in terminal
            except:
                print("500 lost connect to server")
                shutdownFlag = 1

    client_socket.close()  # close the connection

if __name__ == '__main__':
    client_program()
