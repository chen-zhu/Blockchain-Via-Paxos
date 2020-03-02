import xml.etree.ElementTree as ET
import socket
import sys
import json
import copy
import random
import string
import time
import copy
import threading
import os


def list_clients(): 
	tree = ET.parse('config/clients.xml')
	root = tree.getroot()
	clients = []
	for neighbor in root.iter('client'):
		clients.append({'name':neighbor.find('name').text, 'process_id':neighbor.find('process_id').text, 'ip':neighbor.find('ip').text, 'port':neighbor.find('port').text})
	return clients


def to_client_exist(to_name): 
	clients = list_clients()
	for c in clients:
		if c['name'] == to_name: 
			return True
	return False

def wait_for_recovery(listen_socket, connections):
	while (1):
		time.sleep(1)
		conn, c_address = listen_socket.accept()
		data = conn.recv(1024)
		connections[data] = conn
		print("[SOCKET] Client " + data + " is online again.")
		print(connections)
		return conn

def take_snapshot(genesis, commits, client_name):
	#commits --> might contain pending transactions~
	arr = {
		"genesis": genesis,
		"commits": commits
	}
	f = open("seed/snapshot-" + client_name, "w")
	f.write(json.dumps(arr))
	f.close()

#if no snapshot file is present, then load form the default initial file!
def load_snapshot(genesis, commits, client_name): 
	#print("Load snapshot for the client "+ client_name)
	#default, load the seed blockchain file!
	file_name = "seed/blockchain_seed-" + client_name

	#if snapshot exist, it means that it is a recovering phase!
	if os.path.exists("seed/snapshot-" + client_name):
		file_name = "seed/snapshot-" + client_name
		print("[SOCKET] Server Resume Detected. Loading Snapshot... ")
	
	f = open(file_name, "r")
	raw = f.read()
	if len(raw) > 0: 
		data = json.loads(raw)
		for cmt in data["commits"]:
			commits.append({"from": str(cmt["from"]), "to": str(cmt["to"]), "amt": str(cmt["amt"])})
		for blc in data["genesis"]: 
			block = []
			for cmt in blc:
				block.append({"from": str(cmt["from"]), "to": str(cmt["to"]), "amt": str(cmt["amt"])})
			genesis.append(block)



def snapshot_reset():
	if os.path.exists("seed/snapshot-A"):
		os.remove("seed/snapshot-A")
	if os.path.exists("seed/snapshot-B"):
		os.remove("seed/snapshot-B")
	if os.path.exists("seed/snapshot-C"):
		os.remove("seed/snapshot-C")







