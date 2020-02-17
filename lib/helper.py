import xml.etree.ElementTree as ET


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




