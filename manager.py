import socket
import sys
import json
import copy
import random
import string
import time
import copy
from pprint import pprint
import threading

from socket import error as socket_error

from lib import blockchain
from lib.helper import list_clients, to_client_exist
#usage: manager.php (port_num) (process_id) (client_names) (ip)

if len(sys.argv) != 5: 
	print('exit')
	sys.exit(1)

print("*****************************************************\n Client Name: " + sys.argv[3] + "\n*****************************************************\n\n")

clients = list_clients()
lock = threading.Lock()
bc = blockchain.blockchain(sys.argv[3], sys.argv[2], sys.argv[4], sys.argv[1])

#initialize connections
bc.go_online()

#create threads to listen!
bc.run_socket_threads()





while True:
	text = raw_input("")
	split = text.split()
	if len(split) == 0: 
		continue
	elif len(split) == 2: 
		if to_client_exist(split[0]) == False:
			print("Client does not exist.\n")
			continue
		elif split[0] == sys.argv[3]:
			print("Cannot transfer money to self!")
			continue
		if not split[1].isdigit() or int(split[1]) < 0 :
			print("Invalid Amount. Transaction amount must be a positive integer.")
			continue
		
		#TODO: trx details goes here!
		bc.transaction(split[0], int(split[1]))


	elif split[0] == 'balance':
		balance = bc.check_balance()
		print("Current Client Balance: " + str(balance))
	elif split[0] == 'debug':	
		bc.print_blockchain()
	else: 
		print("Invalid Input.\n")















