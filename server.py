# Aizhan Uristembek

from socket import *
from collections import defaultdict
import time
import os
import json
import threading

# initialize hash tables
# peers[ (host, port) ] = list(filenames)
# files[ filename ] = list[(info, peer address)]
# server[ (host, port) ] = (host, port)
peers = defaultdict(list)
files = defaultdict(list)
server = dict()
lock = threading.Lock()

def serve( csock, addr ):
	# Initialize connection
	msg = csock.recv(2048).decode()
	if msg != "HELLO":
		print("Undetermined command")
		csock.close()
		return
	csock.send("HI".encode())

	# work until client exits
	while 1:
		# read msg
		msg = csock.recv(2048).decode()
		# search
		if msg[:6] == 'SEARCH':
			csock.send(browse(msg[8:], addr).encode())
		# bye
		elif msg == 'BYE':
			bye(addr)
			break
		# add
		else:
			csock.send(add(msg, addr).encode())

	# close socket
	print("Closing socket {}".format(addr))
	csock.close()

def add(msg, addr):
	# ADDING
	# no files case
	if len(msg) == 0:
		print("Empty msg")
		return 'FAILURE'
	# convert string to list
	listOfFiles = json.loads(msg)
	# add info to database
	lock.acquire()
	for f in listOfFiles:
		server[addr] = f[-1]
		peers[addr].append(f[0])
		files[f[0]].append(f[1:])
	lock.release()
	return 'SUCCESS'	

def browse(filename, addr):
	# SEARCHING
	# If no file sent, Forbid the access
	if len(peers[addr]) == 0:
		print("No file added. Closing connection")
		return '403'
	# Search for peers and return the result
	res = []
	for f in files[filename]:
		if f[-1] != server[addr]:
			res.append(f)
	if len(res) == 0:
		return 'NOT FOUND'
	return 'FOUND: ' + json.dumps(res)

def bye(addr):
	# CLOSING
	# Deleted files
	lock.acquire()
	for f in peers[addr]:
		i = 0
		while i < len(files[f]):
			if files[f][i][-1] == server[addr]:
				del files[f][i]
			else:
				i += 1
		if len(files[f]) == 0:
			del files[f]
	# Delete info from peers table
	del peers[addr]
	# Delete server info for peer
	del server[addr]
	lock.release()

def main():
	# Configure server
	ssock = socket()
	host = gethostname()
	port = 9999
	ssock.bind((host, port)) 

	ssock.listen(5)
	print("The server is ready to receive")

	# Work non-stop
	while 1:
		# Wait for clients and create thread for each
		csock, addr = ssock.accept()
		print("Request accepted from (address, port) tuple: %s" % (addr,))
		threading.Thread(target=serve, args=(csock,addr,)).start()

main()
