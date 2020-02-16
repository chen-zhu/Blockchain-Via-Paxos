import multiprocessing
import socket
import sys
import json
import copy
import random
import string
import copy
from pprint import pprint
import threading

from socket import error as socket_error


if len(sys.argv) != 5: 
	print('exit')
	sys.exit(1)

print("*****************************************************\n Client Name: " + sys.argv[3] + "\n*****************************************************\n\n")




