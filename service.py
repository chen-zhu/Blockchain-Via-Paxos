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
acc_num = 0 #accepted request num --> request_num * 10 + id!
acc_val = 0 #accepted request value

#if this client is trying to be a leader, use this array to decide if majority is reached!
receive_ack = []
initial_val = ""
receive_accpeted = []

paxos_runing_flag = 0

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
#whenever this client starts, it load snapshot! 
load_snapshot(genesis, commits, client_name)
print("\n\n")

#print(commits)

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
	for commits_block in genesis:
		for trx in commits_block: 
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
	
	print("--------GENESIS--------")
	for block in genesis:
		print(u'|         \u25bc           |') 
		for trx in block: 
			print_str = "| From " + trx['from'] + " To " + trx['to'] + " Amt: " + str(trx['amt'])
			if len(str(trx['amt'])) >= 2: 
				print_str += " |"
			else: 
				print_str += "  |"
			print(print_str)
		print("-----------------------")

	print("\n\n-----LOCAL-COMMITS-----")
	print(u'|         \u25bc           |') 
	for trx in commits: 
		print_str = "| From " + trx['from'] + " To " + trx['to'] + " Amt: " + str(trx['amt'])
		if len(str(trx['amt'])) >= 2: 
			print_str += " |"
		else: 
			print_str += "  |"
		print(print_str)
	print("-----------------------")
	balance = check_balance()
	print(">>> Current Request <NUMBER>: " + str(request_num))
	print(">>> Current Client <BALANCE>: " + str(balance))


def prepare():
	global request_num, client_id, BallotNum, initial_val, commits, client_name, paxos_runing_flag, lock
	#print('[debug] >>> prepare')
	lock.acquire()
	paxos_runing_flag = 1
	request_num += 1
	BallotNum = request_num * 10 + int(client_id)
	msg_body = {
		"type": "prepare",
		"request_num": request_num,
		"owner_id": client_id, 
		"BallotNum": BallotNum, 
	}
	lock.release()
	#pass in leader name here~ 
	#initial_val = json.dumps(commit)
	initial_val = client_name
	time.sleep(5)
	broadcast(json.dumps(msg_body))



#client receive prepare and try to promise
def promise(received, via_socket): 
	global genesis,commits
	global request_num, client_id, BallotNum
	global acc_num, acc_val, lock

	#print('[DEBUG] >>> Send Ack')

	if received["BallotNum"] >= BallotNum:
		lock.acquire()
		request_num = received["request_num"]
		BallotNum = received["BallotNum"]
		msg_body = {
			"type": "promise",
			"BallotNum": BallotNum, 
			"request_num": request_num,
			"acc_num": acc_num, 
			"acc_val": acc_val,
		}
		lock.release()
		via_socket.sendall(json.dumps(msg_body))
	else: 
		msg_body = {
			"type": "rej",
			"request_num": request_num,
			"BallotNum": BallotNum,
		}
		via_socket.sendall(json.dumps(msg_body))
		#print("received smaller BallotNum. Do nothing.") 

#Leader: after receive ack, process and send accept if necessary~
#received from Majority!
def accept(): 
	global receive_ack, initial_val, request_num, BallotNum, lock
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

	lock.acquire()
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
	lock.release()
	print("[ACCEPT] >>> Final Leader Chosen: " + myVal)
	broadcast(json.dumps(msg_body))

#Client received accept from the leader~
def accepted(received, via_socket):
	global request_num, client_id, BallotNum
	global acc_num, acc_val
	global commits, lock

	if (received["BallotNum"] >= BallotNum): 
		lock.acquire()
		acc_num = received["BallotNum"]
		acc_val = received["value"]
		msg_body = {
			"type": "accepted", 
			"BallotNum": received["BallotNum"],
			"original_prop_value": received["value"], 
			"value": json.dumps(commits)
		}
		lock.release()
		via_socket.sendall(json.dumps(msg_body))

#Leader after receive accpeted msg from majority, 
#commit action in place.
def commit():
	global receive_accpeted, client_name
	global genesis, commits, acc_val, paxos_runing_flag, BallotNum, lock

	block = []
	#1. add everything to blockchain
	lock.acquire()
	for b in receive_accpeted: 
		trx_array = json.loads(b["value"])
		for trx in trx_array: 
			block.append(trx)

	for trx in commits:
		block.append(trx)
	
	if len(block) > 0:
		genesis.append(block)
		
	commits = []
	acc_val = 0
	take_snapshot(genesis, commits, client_name)

	msg_body = {
		"type": "commit",
		"BallotNum": BallotNum,
		"transactions": json.dumps(block)
	}
	lock.release()
	
	initial_val = ""
	broadcast(json.dumps(msg_body))

	paxos_runing_flag = 0


def process_commit(received):
	global receive_accpeted, client_name
	global genesis, commits, acc_val, lock, paxos_runing_flag

	lock.acquire()
	transactions = json.loads(received["transactions"])
	if len(transactions) > 0:
		genesis.append(transactions)
	commits = []
	take_snapshot(genesis, commits, client_name)
	acc_val = 0
	paxos_runing_flag = 0
	lock.release()


def paxos_call():
	print('[INFO] >>> Paxos Running.')
	prepare()

def request_insert(type, received): 
	global hard_code_majority, receive_ack, receive_accpeted, client_name, lock

	if type == "promise": 
		lock.acquire()
		receive_ack.append(received)
		lock.release()
	elif type == "accepted":
		#only append to accept IFF the originla value(leader) is itself!
		if(received["original_prop_value"] == client_name): 
			lock.acquire()
			receive_accpeted.append(received)
			lock.release()

def majority_trigger(type):
	global hard_code_majority, receive_ack, receive_accpeted, client_name, lock
	if type == "promise": 
		if len(receive_ack) >= hard_code_majority: 
			return True
		else: 
			return False
	elif type == "accepted": 
		if len(receive_accpeted) >= hard_code_majority: 
			return True
		else: 
			return False

def process_received_msg(received_json, from_socket):
	global connections, BallotNum, receive_ack, receive_accpeted, request_num, paxos_runing_flag, lock, genesis
	received = json.loads(received_json)
	type = received["type"]
	from_client = connections.keys()[connections.values().index(from_socket)]
	#make it print like normal... add lock here...
	if not type == "recover": 
		lock.acquire()
		print("[DEBUG LOG] >>> " + type + " From [" + from_client + "] BallotNum: " + str(received.get("BallotNum")))
		lock.release()

	if type == "prepare": #client receive prepare! 
		promise(received, from_socket)
	elif type == "promise": #leader receive ack from majority clients
		request_insert(type, received)
		if majority_trigger(type):
			print("[DEBUG LOG] >>> Majority Reached. Processing 'Promise' messages...")
			accept()
			lock.acquire()
			receive_ack = [] #reset receive_ack~
			lock.release()
	elif type == "accept": #client receive accept from leader
		accepted(received, from_socket)
	elif type == "accepted": #leader receive accepted from majority clients
		request_insert(type, received)
		if majority_trigger(type):
			print("[DEBUG LOG] >>> Majority Reached. Processing 'Accepted' messages...")
			commit()
			lock.acquire()
			receive_accpeted = []
			lock.release()
	elif type == "commit": #client receive commit from leader~
		process_commit(received)
	elif type == "rej": 
		lock.acquire()
		request_num = received["request_num"]
		lock.release()
		print("[DEBUG LOG] >>> REJ detected. Prepared Value/BallotNum has been ignored by " + from_client + ".")
	elif type == "recover": 
		#when this client re-connect, it will receive recover msg from existing client and compare blockchain. 
		lock.acquire()
		#1. update local request_num first
		request_num = received["request_num"]

		#2. compare genesis and insert the missing block~
		tmp_genesis = []
		for blc in received["genesis"]: 
			block = []
			for cmt in blc:
				block.append({"from": str(cmt["from"]), "to": str(cmt["to"]), "amt": str(cmt["amt"])})
			tmp_genesis.append(block)
			block = []

		#validate received genesis --> make sure that all my existing genesis exist in received. OW, put it on 
		#local commit.
		for check_blk in genesis: 
			#if one block is not in other's, then add it to local log and paxos again.
			if not check_blk in tmp_genesis: 
				for check_cmt in check_blk: 
					commits.append(check_cmt)

		genesis = tmp_genesis
		lock.release()
	else: 
		print("")

def recovering(listen_socket, name): 
	global genesis, request_num
	msg_body = {
		"type": "recover",
		"request_num": request_num,
		"genesis": genesis
	}
	listen_socket.sendall(json.dumps(msg_body))


def socket_keep_receiving(listen_socket, from_client):
	global passive_socket
	global connections, hard_code_majority, lock, receive_ack, receive_accpeted
	listen_socket.setblocking(0)

	while True:
		try:
			time.sleep(1)
			data = listen_socket.sendall("HeartBeat")
			data = listen_socket.recv(1024 * 10)
			data = data.replace("HeartBeat", "")
			if len(data)>0 and not data == "": 
				new_json = data.replace("}{", "}-----{") 
				split_list = new_json.split("-----")
				for sl in split_list:
					process_received_msg(sl, listen_socket)
			
		except socket_error as e:
			if e.errno == 54 or e.errno == 32:
				hard_code_majority -= 1
				print("[SOCKET] client " + from_client + " is currently offline! Majority Count Changed To: " + str(hard_code_majority))
				#sooo messy here......if client is down, majority changes --> retrigger actions
				if majority_trigger("promise"):
					accept()
					lock.acquire()
					receive_ack = [] #reset receive_ack~
					lock.release()

				if majority_trigger("accepted"):
					commit()
					lock.acquire()
					receive_accpeted = []
					lock.release()

				useless = connections.pop(from_client)
				listen_socket = wait_for_recovery(passive_socket, connections)
				hard_code_majority += 1
				listen_socket.setblocking(0)
				#then push my blockchain info to this client.
				recovering(listen_socket, from_client)


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
			print("[TRX]: Transaction Succeeded")
			take_snapshot(genesis, commits, client_name)
		else:
			paxos_call()
			take_snapshot(genesis, commits, client_name)
			for i in range(200): 
				if paxos_runing_flag == 0: 
					break
				else: 
					time.sleep(0.5)
			balance = check_balance()
			if balance >= int(split[1]):
				commits.append({"from":client_name, "to":split[0], "amt":int(split[1])})
				print("[TRX]: Transaction Succeeded")
				take_snapshot(genesis, commits, client_name)
			else: 
				print("Inefficient balance detected.")

	elif split[0] == 'balance' or split[0] == 'PrintBalance':
		balance = check_balance()
		print("Current Client Balance: " + str(balance))
	elif split[0] == 'debug' or split[0] == 'check' or split[0] == 'PrintLog' or split[0] == 'PrintBlockchain':	
		print_blockchain()
	else: 
		print("Invalid Input.\n")













