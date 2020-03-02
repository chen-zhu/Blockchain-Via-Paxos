#!/usr/bin/python
import time
import os
import xml.etree.ElementTree as ET
from random import randint
from lib.helper import *

snapshot_reset()

tree = ET.parse('config/clients.xml')
root = tree.getroot()

#try to avoid the annoying address-in-use issue during testing
rand_int = 0 #randint(0, 777)

for neighbor in root.iter('client'):
	random_port_num = int(neighbor.find('port').text) + rand_int
	command = "osascript -e 'tell application \"Terminal\" to do script \"cd ~/Documents/CMPSC_271/Blockchain-Via-Paxos/ && python ./service.py " + str(random_port_num) + " " + neighbor.find('process_id').text + " " + neighbor.find('name').text + " " + neighbor.find('ip').text + " " + " \"' "
	os.system(command)
	time.sleep(3)
