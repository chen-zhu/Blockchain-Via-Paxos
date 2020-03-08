from helper import list_clients
from pprint import pprint
import threading
import socket
import json
from time import *
import copy
import math

class blockchain: 

    #a list that holds commits block.
    genesis = []

    #a list that comtains transaction commits.
    commits = []

    #client connection list. name => connected_socket
    connections = {} 

    #paxos config info
    request_num = 0
    leader_election_vote = 0
    acc_num = 0 #accepted request num --> request_num * 10 + id!
    acc_val = 0 #accepted request value

    #if this client is trying to be a leader, use this array to decide if majority is reached!
    receive_ack = []
    initial_val = ""

    receive_accpeted = []

    lock = threading.Lock()

    def __init__(self, name, id, ip, port): 
        self.name = name
        self.id = id
        self.ip = ip
        self.port = port
        self.clients = list_clients()

    def go_online(self): 
        import socket
        from socket import error as socket_error

        #clients = list_clients()

        #active mode connecting here!
        for c_info in self.clients: 
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

        while (len(self.connections) < len(self.clients) - 1 ): 
            sleep(1)
            conn, c_address = socket.accept()
            data = conn.recv(1024)
            self.connections[data] = conn
        print(self.connections)


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
        print('[debug] >>> Paxos starts.')
        self.receive_ack = []

        #todo: clean up initial_val with new commit json string!

        self.leader_election()

        #must receive majority vote!
        #if(self.leader_election_vote >= math.ceil(len(self.clients)/2)): 
            #accept request
            #commit request



    def leader_election(self):
        print('start leader election.')


    #Leader's Action
    def prepare(self): 
        print('[debug] >>> prepare')
        self.request_num ++
        msg_body = {
            "type": "prepare",
            "request_num": self.request_num,
            "owner_id": self.id
        }
        self.broadcast(json.dumps(msg_body))

    #Client's Action
    def ack(self, json_body, via_socket): 
        print('[debug] >>> ack')
        received = json.loads(json_body)

        if (int(received["request_num"])*10 + int(received["owner_id"])) >= (self.request_num * 10 + self.id):
            self.request_num = received["request_num"]
            msg_body = {
                "type": "ack",
                "request_num": self.request_num,
                "owner_id": received["owner_id"], 
                "acc_num": self.acc_num, 
                "acc_val": self.acc_val,
            }
            via_socket.sendall(json.dumps(msg_body))
        #else, do we need to send reject?

    #Leader's Action
    def accept(self): 
        print('[debug] >>> accept')
        myVal = ""

        #self.receive_ack
        vals = []
        val_with_highest_req_num = ""

        highest_req_num = 0
        for ack in self.receive_ack: 
            vals.append(ack["acc_val"])
            if len(ack["acc_val"]) > 0 and highest_req_num < int(ack["request_num"]) * 10 + int(ack["owner_id"]): 
                val_with_highest_req_num = ack["acc_val"]

        if len(vals) == 0: 
            myVal = self.initial_val
        else
            myVal = val_with_highest_req_num

        msg_body = {
            "type": "accept", 
            "request_num": self.receive_ack[0]["request_num"], 
            "owner_id": self.receive_ack[0]["owner_id"], 
            "value": myVal
        }

        self.broadcast(json.dumps(msg_body))


    #Client's Action
    def accepted(self, json_body, via_socket): 
        print('[debug] >>> accepted')
        received = json.loads(json_body)

        if (int(received["request_num"])*10 + int(received["owner_id"])) >= (self.request_num * 10 + self.id): 
            self.acc_num = int(received["request_num"])*10 + int(received["owner_id"])
            self.acc_val = received["value"]
            msg_body = {
                "type": "accepted", 
                "request_num": self.acc_num, 
                "owner_id": received["owner_id"], 
                "original_value": received["value"], #use it for verification on the leader side?
                "value": json.dumps(self.commits)
            }
            via_socket.sendall(json.dumps(msg_body))   

    #Leader's Action
    def commit(self): 
        print('[debug] >>> commit')
        #create the big block
        for accepted in receive_accpeted: 



    def socket_listen(self, socket): 
        while True:
            #todo: modify this receive msg buffer size!
            data = socket.recv(1024*4)
            if len(data)>0: 
                #weired thread & socket issue. 
                new_json = data.replace("}{", "}-----{") 
                split_list = new_json.split("-----")
                for sl in split_list:
                    process_received_msg(sl, socket)  


    def run_socket_threads(self):
        for c_socket in self.connections: 
            thread = threading.Thread(target=self.socket_listen, args=(c_socket, ))
            thread.start()

    def broadcast(self, json):
        for socket in self.connections:
            if c_info['name'] == self.name:
                continue
            socket.sendall(json)














