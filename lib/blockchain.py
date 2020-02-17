from helper import list_clients
from pprint import pprint
import multiprocessing
import socket
import json
from time import *
import copy

class blockchain: 
    #a list that holds commits block.
    genesis = []

    #a list that comtains transaction commits.
    commits = []

    #client connection list. name => connected_socket
    connections = {} 

    def __init__(self, name, id, ip, port): 
        self.name = name
        self.id = id
        self.ip = ip
        self.port = port

    def go_online(self): 
        import socket
        from socket import error as socket_error

        clients = list_clients()

        #active mode connecting here!
        for c_info in clients: 
            if c_info['name'] == self.name:
                continue
            sleep(1)
            print("[Active Socket]Connecting to the client " + c_info['name'] + " > " + c_info['ip'] + ":" + c_info['port'] + ".....")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((c_info['ip'], int(c_info['port'])))
                sock.sendall(self.name)
                self.connections[c_info['name']] = sock
                print("[Active Socket]Connected to the client " + c_info['name'] + "\n")
            except socket_error as serr:
                print("[Active Socket]Cannot reach the client " + c_info['name'] + "\n")

        print("Client enters [Passive] connecting mode ... ...\n")
        socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.bind((self.ip, int(self.port)))
        socket.listen(24)
        blockchain_socket = None

        while (len(self.connections) < len(clients) - 1 ): 
            sleep(1)
            conn, c_address = socket.accept()
            data = conn.recv(1024)
            self.connections[data] = conn
        #print(self.connections)


    def check_balance(self):
        balance = 100
        
        #calculate aggregated list
        for commits in self.genesis:
            for trx in commits: 
                if trx['from'] == self.name:
                    balance -= int(trx['amt'])
                elif trx['to'] == self.name: 
                    balance += int(trx['amt'])

        #calculate commits list
        for trx in self.commits: 
                if trx['from'] == self.name:
                    balance -= int(trx['amt'])
                elif trx['to'] == self.name: 
                    balance += int(trx['amt'])

        return balance

    def transaction(self, to, amt): 
        balance = self.check_balance()
        #directly insert
        if balance >= amt:
            self.commits.append({"from":self.name, "to":to, "amt":amt})
        #else, no enough balance, then paxos call & retry it again.
        else : 
            self.paxos_call()
            if self.check_balance() >= amt: 
                self.commits.append({"from":self.name, "to":to, "amt":amt})
            else : 
                print("Inefficient balance detected.")


    def print_blockchain(self):
        print("Genesis/Blockchain List: ")
        for commits in self.genesis:
            print(u'\u25bc') 
            for trx in commits: 
                print("From " + trx['from'] + " To " + trx['to'] + " Amt: " + str(trx['amt']))

        print("\nLocal Logs List:" + u'\u25bc')
        for trx in self.commits: 
            print("From " + trx['from'] + " To " + trx['to'] + " Amt: " + str(trx['amt']))


    #also remember to put commits inside genesis!
    def paxos_call(self): 
        print('paxos call goes here.')








