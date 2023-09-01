#!/usr/bin/env python3
################################################################
# azelSend.py - Send Azimuth/Elevation commands to a Waveshare Pan/Tilt assembly over the network
#
# HISTORICAL INFORMATION -
#
#  2022-03-14  msipin  Created from current version of our github "warpigIV" repository's balloonSend.py
################################################################

from scapy.all import *
import sys
import subprocess

# Waveshare pan/tilt assembly's IP address -
dst_ip1="11.11.11.11"
#dst_ip1="127.0.0.1"


# Takes 2 arguments. 1st argument is azimuth (in degrees). 2nd argument is elevation (in degrees above horizon)
numargs = len(sys.argv)
if (numargs != 3):
    print("\nusage: %s <azimuth> <elevation>\n" % sys.argv[0])
    sys.exit(1)

# This command is argument[0]

# Azimuth (in degrees) is argument[1]
AZ = int(sys.argv[1])

# Elevation (in degrees) is argument[2]
EL = int(sys.argv[2])

#data1= "AZ:30 EL:45"
data1= "AZ:" + str(AZ) + " EL:" + str(EL)
#data1= "JIBBERISH!"

data=data1
print("Pan/Tilt data: [%s]\n" % data1)


src_prt=3131
dst_prt=3131

# Send to dst_ip -
packet1 = IP(dst=dst_ip1)/UDP(dport=dst_prt, sport=src_prt)/data
print(packet1)
send(packet1,verbose=False) 


quit()

