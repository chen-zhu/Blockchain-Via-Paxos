import socket
import sys
import json
import copy
import random
import string
import time
import copy
import threading

from pprint import pprint
from socket import error as socket_error
from lib.helper import *
#usage: manager.php (port_num) (process_id) (client_names) (ip)

if len(sys.argv) != 5: 
	print('exit')
	sys.exit(1)

print("*****************************************************\n Client Name: " + sys.argv[3] + "\n*****************************************************\n\n")

clients = list_clients()
lock = threading.Lock()

client_name = sys.argv[3]
client_id = sys.argv[2]
client_ip = sys.argv[4]
client_port = sys.argv[1]
hard_code_majority = 2

#a list that holds commits block.
genesis = []
#a list that comtains transaction commits.
commits = []
#client connection list. name => connected_socket
connections = {} 
#paxos config info
request_num = 0
BallotNum = 0
leader_election_vote = 0
acc_num = 0 #accepted request num --> request_num * 10 + id!
acc_val = 0 #accepted request value

#if this client is trying to be a leader, use this array to decide if majority is reached!
receive_ack = []
initial_val = ""
receive_accpeted = []

#initialize connections
for c_info in clients: 
	if c_info['name'] == client_name:
		continue
	time.sleep(1)
	print("[SOCKET] ACTIVE - Connecting to the client " + c_info['name'] + " > " + c_info['ip'] + ":" + c_info['port'] + ".....")
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.connect((c_info['ip'], int(c_info['port'])))
		sock.sendall(client_name)
		connections[c_info['name']] = sock
		print("[SOCKET] ACTIVE - Connected to the client " + c_info['name'] + "\n")
	except socket_error as serr:
		print("[SOCKET] ACTIVE - Cannot reach the client " + c_info['name'] + "\n")

print("[SOCKET] PASSIVE - Client enters [PASSIVE] connecting mode ... ...\n")
passive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
passive_socket.bind((client_ip, int(client_port)))
passive_socket.listen(24)

while (len(connections) < len(clients) - 1 ): 
	time.sleep(1)
	conn, c_address = passive_socket.accept()
	data = conn.recv(1024)
	connections[data] = conn
print(connections)

print("\n\n")

#*********************BlockcChain Main Body Function************************
def broadcast(json):
	global connections
	global client_name
	for name, socket in connections.iteritems():
		if name == client_name:
			continue
		socket.sendall(json)

def check_balance():
	initial_balance = 10
	global genesis, commits
	global client_name
	#calculate aggregated list
	for commits in genesis:
		for trx in commits: 
			if trx['from'] == client_name:
				initial_balance -= int(trx['amt'])
			elif trx['to'] == client_name: 
				initial_balance += int(trx['amt'])
	#calculate commits list
	for trx in commits: 
		if trx['from'] == client_name:
			initial_balance -= int(trx['amt'])
		elif trx['to'] == client_name: 
			initial_balance += int(trx['amt'])
	return initial_balance

def print_blockchain():
	global genesis, commits
	global client_name
	global request_num
	print("Current Request Number: " + str(request_num))
	print("Genesis/Blockchain List: ")
	for block in genesis:
		print(u'\u25bc') 
		for trx in block: 
			print("From " + trx['from'] + " To " + trx['to'] + " Amt: " + str(trx['amt']))

	print(" >>> Local Logs List:" + u'\u25bc')
	for trx in commits: 
		print("From " + trx['from'] + " To " + trx['to'] + " Amt: " + str(trx['amt']))



def prepare():
	global request_num, client_id, BallotNum, initial_val, commits
	print('[debug] >>> prepare')
	request_num += 1
	BallotNum = request_num * 10 + int(client_id)
	msg_body = {
		"type": "prepare",
		"request_num": request_num,
		"owner_id": client_id, 
		"BallotNum": BallotNum, 
	}
	initial_val = json.dumps(commits)
	broadcast(json.dumps(msg_body))

#client receive prepare and try to promise
def promise(received, via_socket): 
	global genesis,commits
	global request_num, client_id, BallotNum
	global acc_num, acc_val

	#print('[DEBUG] >>> Send Ack')

	if received["BallotNum"] >= BallotNum:
		request_num = received["request_num"]
		BallotNum = received["BallotNum"]
		msg_body = {
			"type": "promise",
			"BallotNum": BallotNum, 
			"request_num": request_num,
			"acc_num": acc_num, 
			"acc_val": acc_val,
		}
		via_socket.sendall(json.dumps(msg_body))
	else: 
		print("received smaller BallotNum. Do nothing.") 

#Leader: after receive ack, process and send accept if necessary~
#received from Majority!
def accept(): 
	global receive_ack, initial_val, request_num, BallotNum
	print('[debug] >>> accept')
	myVal = ""

	vals = []
	val_with_highest_req_num = ""
	highest_req_num = 0
	send_req_num = 0

	for ack in receive_ack: 
		if (not ack["acc_val"] == 0):
			vals.append(ack["acc_val"])
		if (not ack["acc_val"] == 0) and highest_req_num < ack["acc_num"]: 
			val_with_highest_req_num = ack["acc_val"]
			highest_req_num = ack["BallotNum"]
			send_req_num = ack["request_num"]

	if len(vals) == 0: 
		myVal = initial_val
		send_req_num = request_num
	else: 
		myVal = val_with_highest_req_num

	msg_body = {
		"type": "accept", 
		"request_num": send_req_num, 
		"BallotNum": BallotNum,
		"value": myVal
	}

	broadcast(json.dumps(msg_body))

#Client received accept from the leader~
def accepted(received, via_socket):
	global request_num, client_id, BallotNum
	global acc_num, acc_val
	global commits

	print('[debug] >>> accepted')

	if (received["BallotNum"] >= BallotNum): 
		acc_num = received["BallotNum"]
		acc_val = received["value"]
		msg_body = {
			"type": "accepted", 
			"BallotNum": received["BallotNum"],
			"original_prop_value": received["value"], 
			"value": json.dumps(commits)
		}
		via_socket.sendall(json.dumps(msg_body))

#Leader after receive accpeted msg from majority, 
#commit action in place.
def commit():
	global receive_accpeted
	global genesis, commits

	block = []
	#1. add everything to blockchain
	for b in receive_accpeted: 
		trx_array = json.loads(b["value"])
		for trx in trx_array: 
			block.append(trx)

	for trx in commits:
		block.append(trx)

	genesis.append(block)
	commits = []

	msg_body = {
		"type": "commit",
		"transactions": json.dumps(block)
	}
	broadcast(json.dumps(msg_body))
	#anything else goes here?

def process_commit(received):
	global receive_accpeted
	global genesis, commits

	transactions = json.loads(received["transactions"])
	genesis.append(transactions)
	commits = []


def paxos_call():
	print('[debug] >>> Paxos starts.')
	prepare()

def majority_reached(type, received): 
	global hard_code_majority, receive_ack, receive_accpeted

	if type == "promise": 
		receive_ack.append(received)
		#Yeahhh majority goes here!
		if len(receive_ack) >= hard_code_majority: 
			return True
		else: 
			return False
	elif type == "accepted":
		receive_accpeted.append(received)
		if len(receive_accpeted) >= hard_code_majority: 
			return True
		else: 
			return False

def process_received_msg(received_json, from_socket):
	global connections, BallotNum, receive_ack, receive_accpeted

	received = json.loads(received_json)
	type = received["type"]
	from_client = connections.keys()[connections.values().index(from_socket)]
	print("[DEBUG LOG] >>> " + type + " From [" + from_client + "]: " + received_json)

	if type == "prepare": #client receive prepare! 
		promise(received, from_socket)
	elif type == "promise": #leader receive ack from majority clients
		#Majority involved!
		#wait until receive_ack is fulfilled!
		if majority_reached(type, received):
			print("Majority Ack received. Processing ACK messages...")
			accept()
			receive_ack = [] #reset receive_ack~
	elif type == "accept": #client receive accept from leader
		accepted(received, from_socket)
	elif type == "accepted": #leader receive accepted from majority clients
		if majority_reached(type, received):
			print("Majority Accepted received. Processing Accepted messages...")
			commit()
			receive_accpeted = []
	elif type == "commit": #client receive commit from leader~
		process_commit(received)
	else: 
		print("Unknown response received.")


def socket_keep_receiving(listen_socket, from_client):
	global passive_socket
	global connections
	
	while True:
		listen_socket.setblocking(0)
		time.sleep(1)
		try:
			data = listen_socket.sendall("HeartBeat")
			data = listen_socket.recv(1024 * 10)
			if len(data)>0 and "HeartBeat" not in data: 
				#print("received. " + data)
				new_json = data.replace("}{", "}-----{") 
				split_list = new_json.split("-----")
				for sl in split_list:
					process_received_msg(sl, listen_socket)
		except socket_error as e:
			if e.errno == 54 or e.errno == 32:
				print("[SOCKET] client " + from_client + " is currently offline!")
				listen_socket = wait_for_recovery(passive_socket, connections)

#create threads for each connected socket so that it keeps receiving message.
for name, socket in connections.iteritems():
	listen_thread = threading.Thread(target=socket_keep_receiving, args=(socket, name, ))
	listen_thread.start()


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
		
		balance = check_balance()
		if balance >= int(split[1]):
			commits.append({"from":client_name, "to":split[0], "amt":int(split[1])})
		else:
			paxos_call()
			#TODO: figure out a way to wait until paxos terminates~
			if balance >= int(split[1]):
				commits.append({"from":client_name, "to":split[0], "amt":int(split[1])})
			else: 
				print("Inefficient balance detected.")

	elif split[0] == 'balance':
		balance = check_balance()
		print("Current Client Balance: " + str(balance))

	elif split[0] == 'debug':	
		print_blockchain()
	else: 
		print("Invalid Input.\n")













