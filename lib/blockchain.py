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
        print("Going online!")

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

    #also remember to put commits inside genesis!
    def paxos_call(self): 
        print('paxos call goes here.')
