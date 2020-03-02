#!/usr/bin/python
import time
import os
import pathlib
import xml.etree.ElementTree as ET
from random import randint
from lib.helper import *

snapshot_reset()

tree = ET.parse('config/clients.xml')
root = tree.getroot()

#try to avoid the annoying address-in-use issue during testing
rand_int = 0 #randint(0, 777)

service_path = str(pathlib.Path().absolute()) + "/"

for neighbor in root.iter('client'):
	random_port_num = int(neighbor.find('port').text) + rand_int
	command = "osascript -e 'tell application \"Terminal\" to do script \"cd " + service_path + " && python ./service.py " + str(random_port_num) + " " + neighbor.find('process_id').text + " " + neighbor.find('name').text + " " + neighbor.find('ip').text + " " + " \"' "
	os.system(command)
	print(">>> Client " + neighbor.find('name').text + " Command: \ncd " + service_path + " && python ./service.py " + str(random_port_num) + " " + neighbor.find('process_id').text + " " + neighbor.find('name').text + " " + neighbor.find('ip').text + "\n\n")
	time.sleep(3)
