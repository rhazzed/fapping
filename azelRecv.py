#!/usr/bin/env python3
################################################################
# azelRecv.py - Receive Azimuth/Elevation commands over a network socket and drive a Waveshare Pan/Tilt assembly to those angles
#
# HISTORICAL INFORMATION -
#
#  2022-03-14  msipin  Created from current version of our github "warpigIV" repository's udpClient.py
################################################################

import socket
import sys
import subprocess

HOST = ''   # Symbolic name meaning all available interfaces
##PORT = 1313 # Listening port

# Takes 1 argument. 1st argument is port number to listen on
numargs = len(sys.argv)
if (numargs != 2):
    print("\nusage: %s <listen_port_number>\n" % sys.argv[0])
    sys.exit(1)


PORT = int(sys.argv[1])
print("Starting pan/tilt listener on port %d\n" % PORT)

# Datagram (udp) socket
try :
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('Socket created')
except socket.error as e:
    if hasattr(e,'message'):
        print('Failed to create socket. Message ' + e.message)
    else:
        print('Failed to create socket.')
    sys.exit()


# Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except socket.error as e:
    if hasattr(e,'message'):
        print('Bind failed. Message ' + e.message)
    else:
        print('Bind failed.')
    sys.exit()

print('Socket bind complete')

print('Waiting for clients...')
sys.stdout.flush()
#now keep talking with the client
while 1:
    # receive data from client (data, addr)
    d = s.recvfrom(1024)
    data = d[0].decode().strip()
    addr = d[1]

    if not data:
        continue

    if "AZ:" in data:

        print('    **** ACK ****    Acknowledge Receipt Of: ' + data)

        # Clean up data for passing to goto.py -
        args = data.replace('AZ:','').replace(' EL:',' ').split(' ')
        if len(args) == 2:
            print('args[0]: ' + args[0])
            print('args[1]: ' + args[1])

            proc = subprocess.Popen(['goto.py',args[0],args[1]],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            data1 = proc.stdout.read().decode().rstrip('\r').rstrip('\n').replace('\n',',')
            print("goto.py returned: %s\n" % data1)
        else:
            print("goto.py args not correct length!")

    else:
        print('ABUSE DETECTED: [' + addr[0] + ':' + str(addr[1]) + '] - ' + data)

    sys.stdout.flush()

s.close()

