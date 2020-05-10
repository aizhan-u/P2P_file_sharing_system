# Aizhan Uristembek

from socket import *
import PySimpleGUI as sg
import time
import os
import random
import json
import threading
import filecmp
from shutil import copyfile

folderName = ''

def send(csock, addr):
	msg = csock.recv(2048).decode()
	if msg[:8] == 'DOWNLOAD':
		# get file info
		filename = json.loads(msg[10:])
		# define path in own folder
		path = os.getcwd() + '/' + folderName + '/' + filename[0] + '.' + filename[1]
		info = os.stat(path)
		# send 'FILE: '
		csock.send('FILE: '.encode())
		# send file content
		if info[6] == filename[2]:
			f = open(path, 'rb')
			out = f.read()
			csock.send(out)
			f.close()
	else:
		print("Undetermined command")
	# Close connection
	csock.close()

def serve(ssock):
	print("Ready to accept clients")
	ssock.listen(5)	
	while 1:
		csock, addr = ssock.accept()
		threading.Thread(target=send, args=(csock,addr,)).start()

def add(paths, csock, ssock):
	paths = paths.split(';')
	l = []
	i = 0
	for path in paths:
		# Don't consider empty paths
		if path == '':
			continue
		# Don't send > 5
		if i == 5:
			break
		name = os.path.splitext(os.path.basename(path))
		# Create a copy in own folder to share from that folder in the future
		dest = os.getcwd() + '/' + folderName + '/' + name[0] + name[1]
		if not os.path.exists(dest) or not filecmp.cmp(path, dest):
			copyfile(path, dest )
		info = os.stat(path)
		l.append((name[0], name[1][1:],info[6],time.asctime (time.localtime (info[8])), ssock))
		i += 1
	# SENDING FILES INFO
	csock.send(json.dumps(l).encode())
	return csock.recv(2048).decode()

def browse(filename, csock):
	# SEARCHING
	csock.send(('SEARCH: ' + filename).encode())
	return csock.recv(10240).decode()

def client():
	# CONFIGURATION
	# Create server side
	ssock = socket(AF_INET, SOCK_STREAM)
	host = gethostname()
	port = random.randrange(10000, 60000) % 5000 + 10000
	ssock.bind((host, port))
	server = (host, 9999)
	t = threading.Thread(target=serve, args=(ssock,))
	t.start()

	# Create client side
	csock = socket(AF_INET, SOCK_STREAM)
	port = random.randrange(10000, 60000) % 5000 + 10000
	csock.bind((host, port))

	# Create folder
	global folderName
	folderName = str(port)
	if not os.path.exists(folderName):
		os.mkdir(folderName)

	# Initiate connection
	csock.connect(server)
	csock.send("HELLO".encode())
	msg = csock.recv(2048).decode()
	if msg != "HI":
		print("Undetermined command")
		csock.close()
		return
	
	# Configure GUI
	sg.theme('DarkAmber')

	cb = sg.CalendarButton(button_text='Modification Date',
	    button_color=("white", "black"))

	window = sg.Window('File add', [[sg.In(), sg.FilesBrowse()],
		  [sg.Button('Add'), sg.Button('Next'), sg.Exit()]])

	while True:
		# Open GUI and wait for action
		event, values = window.Read()
		# If a client clicks 'X' or 'Exit' button, go out of the loop
		if event is None or event == 'Exit':
			break
		# Return to file addition
		if event == 'Start':
			window.close()
			window = sg.Window('File add', [[sg.In(), sg.FilesBrowse()], [sg.Button('Add'), sg.Button('Next'), sg.Exit()]])
		# If a client pushes add, call add function and read a server message
		if event == 'Add':
			msg = add(values[0], csock, ssock.getsockname())
			# Sent 0 files
			if msg == 'FAILURE':
				w = sg.Window('Error', [[sg.Text('Choose files')], [sg.Button('Return'), sg.Exit()]])
				event, values = w.Read()
				w.close()
				if event == 'Exit':
					break
			# Information successfully added
			elif msg == 'SUCCESS':
				event = 'Next'
		# Open search window
		if event == 'Next':
			window.close()
			window = sg.Window('File Browse', [[sg.Text('Filename'), sg.InputText()], [sg.Button('Return to Add', key='Start'), sg.Button('Search'), sg.Exit()]])
		# Searching
		if event == 'Search':
			# No file name provided -> let user know
			if values[0] == '':
				w = sg.Window('Error', [[sg.Text('No file name.')]])
				w.Read(timeout=1000)
				w.close()
				continue
			res = browse(values[0], csock)
			# No access to the server
			if res == '403':
				w = sg.Window('Error', [[sg.Text('Forbidden')]])
				w.Read(timeout=1000)
				break
			# Peers not found
			elif res == 'NOT FOUND':
				w = sg.Window('Error', [[sg.Text('No peers found. Try again.')], [sg.Button('Return'), sg.Exit()]])
				event, values = w.Read()
				w.close()
				if event == 'Exit':
					break
			# Found files
			elif res[:5] == 'FOUND':
				# Close this window and open a window with list of peers
				window.close()
				res = json.loads(res[7:])
				col = []
				for i in range(len(res)):
					col.append([sg.Text(str(res[i][-1])), sg.Text(res[i][0]), sg.Text(str(res[i][1])), sg.Text(res[i][2]), sg.Button('Choose {}'.format(i))])
				col.append([sg.Button('Return', key='Next'), sg.Exit()])
				l = [[sg.Slider(range=(1,100), default_value=10, orientation='v', size=(8,20)), sg.Column(col)]]
				window = sg.Window('Results for {}'.format(values[0]), l)
				# Remember the file name
				filename = values[0]
		# When a client chose a peer
		if event[:6] == 'Choose':
			# create download socket
			dsock = socket(AF_INET, SOCK_STREAM)
			port = random.randrange(10000, 60000) % 5000 + 10000
			dsock.bind((host,port))
			# connect to peer
			i = int(event[7:])
			dsock.connect((res[i][-1][0],res[i][-1][1]))
			# prepare a message and send to the peer
			msg = json.dumps((filename, res[i][0], res[i][1]))
			dsock.send(('DOWNLOAD: ' + msg).encode())

			recv = dsock.recv(2048).decode()
			if recv != 'FILE: ':
				print("Undetermined error")
				break
			# Create a file in own directory
			f = open(os.getcwd() + '/' + folderName + '/' + filename + '.' + res[i][0], "wb")
			x = 0
			# Receive file contents
			while x < res[i][1]:
				recv = dsock.recv(2048)
				x += len(recv)
				f.write(recv)
				# Show progress bar (stays long enough for large files)
				if not sg.OneLineProgressMeter('Download', x, res[i][1] - 1, 'key', 'Download in progress'):
					break
			# Close file and socker
			f.close()
			dsock.close()
			# If everything's OK, close the list and show a success window
			# Else: show a failure window and return to list
			if x == res[i][1]:
				window.close()
				window = sg.Window('SUCCESS', [[sg.Text('Successfully downloaded the file!')], [sg.Button('Return', key='Next'), sg.Exit()]])
			else:
				w = sg.Window('FAILURE', [[sg.Text('The server has gone unexpectedly')]])
				w.Read(Timeout = 1000)
	# When done, send a BYE message and close the connection
	csock.send('BYE'.encode())
	csock.close()
	# Close the GUI
	window.close()
	# Force close all threads
	os._exit(0)

client()
