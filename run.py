#!/usr/bin/python
import time
import os
import xml.etree.ElementTree as ET

tree = ET.parse('config/clients.xml')
root = tree.getroot()

for neighbor in root.iter('client'):
	command = "osascript -e 'tell application \"Terminal\" to do script \"cd ~/Documents/CMPSC_271/Blockchain-Via-Paxos/ && python ./manager.py " + neighbor.find('port').text + " " + neighbor.find('process_id').text + " " + neighbor.find('name').text + " " + neighbor.find('ip').text + " " + " \"' "
	os.system(command)
	time.sleep(3)
