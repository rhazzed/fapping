#! /usr/bin/python
############################################
# dump10902sbs.py - A Python program to extract real-time ADS-B aircraft beacon data from one or more
#                   Dump1090 "data.json" URLs and produce SBS-1 BaseStation records from them.
#
# HISTORICAL INFORMATION -
#
#  2017-06-10  msipin  Derived from fa2sbs.py
#  2017-06-11  msipin  Switched from urllib to urllib2
#  2020-10-09  msipin  Changed altitude key from "altitude" to "alt_baro" due to post-2017 PiAware change
############################################

import sys
import math
import urllib2
import json
import time
import datetime
import socket
import sys
import Queue
import threading


GO_LIVE=1      # Set to "1" if you want to "GO LIVE!" (e.g. start the socket server, wait for a connection, etc...)
               # Set to "0" if you want to debug this program (prevents socket server etc. from being started)



HOST = ''  # Symbolic name meaning all available interfaces




# "No Such Number" - Until I can figure out how to filter out non-existent dictionary entries,
# this will be my signal that a dictionary had no value at a given key
NSN=424242424242

# JSON field names - as defined by PiAware's read-from-airplane-data-URL functionality
KEY_ICAO='hex'
KEY_CALLSIGN='flight'
#KEY_LEVEL='altitude' # 2017 key
KEY_LEVEL='alt_baro' # Post-2017 key (don't know when it changed...)
KEY_GSPD='speed'
KEY_TRACK='track'
KEY_LAT='lat'
KEY_LON='lon'
KEY_VERT_RATE='vert_rate'
KEY_SQUAWK='squawk'
KEY_RSSI='rssi'
KEY_AGE='seen'
KEY_VALID_POSITION='validposition'

# Global variables that will hold airplane attribute data (both for display and db writes/reads)
ICAO_HEX=''
ICAO_STR=''
CALLSIGN=''
LEVEL=NSN
GSPD=NSN
TRACK=NSN
LAT=NSN
LON=NSN
VERT_RATE=NSN
SQUAWK=NSN
RSSI=NSN
RANGE=NSN
AGE=NSN
VALID_POSITION=0


SLEEP_INTERVAL=13


def init_display_vars():
    global ICAO_HEX
    global ICAO_STR
    global CALLSIGN
    global LEVEL
    global GSPD
    global TRACK
    global LAT
    global LON
    global VERT_RATE
    global SQUAWK
    global RSSI 
    global RANGE
    global AGE
    global VALID_POSITION

    ICAO_HEX=''
    ICAO_STR=''
    CALLSIGN=''
    LEVEL=NSN
    GSPD=NSN
    TRACK=NSN
    LAT=NSN
    LON=NSN
    VERT_RATE=NSN
    SQUAWK=NSN
    RSSI=NSN
    RANGE=NSN
    AGE=NSN
    VALID_POSITION=0



def get_key(q,conn,live):
    while 1:
        # Block on any data arriving in the queue
        indata = q.get()
        # If "Live", write all data to the socket
        if (live):
            # Write that data to socket
            conn.sendall(indata)
        else:
            # Write data to stdout
            sys.stdout.write(indata)








if (len(sys.argv) <5):
    sys.stderr.write('\nusage: {0} <server_port_number> <receiver_lat> <receiver_long> <ip_address[:port]> [<ip_address2[:port]>...]\n\n'.format(sys.argv[0]))
    sys.stderr.write("server_port_number is required. This is where the program will serve up the data it retrieves.\n")
    sys.stderr.write("receiver_lat and receiver_long are required. All range calculations will be based upon this position.\n\n")
    sys.stderr.write("At least one IP address is required.\n")
    sys.stderr.write("Port number for any IP address is optional, with a default of 8080.\n")
    raise SystemExit

# Pick up Server Port Number
PORT=int(sys.argv[1])

# Pickup IP address
NUMARGS=len(sys.argv)
ARGNO=4



# Pickup receiver lat/lon from the command line
RX_LAT = float(sys.argv[2])
#print '\tRX_LAT = %s' % RX_LAT
RX_LON = float(sys.argv[3])
#print '\tRX_LON = %s' % RX_LON


# Setup the server socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#print 'Socket created'

try:
    s.bind((HOST, PORT))
except socket.error, msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()

#print 'Socket bind to port {0} complete'.format(PORT)

s.listen(10)
print 'Server is listening on port {0}'.format(PORT)

conn=0
addr=0
if (GO_LIVE):
    # wait to accept a connection - blocking call
    conn, addr = s.accept()
    print 'Connected with ' + addr[0] + ':' + str(addr[1])
else:
    print 'Connected with (self - for DEBUGGING!)'

# End if-go-live!


# Start the socket-handling thread
q = Queue.Queue()
t = threading.Thread(target=get_key, args = (q,conn,GO_LIVE))
t.daemon = True
t.start()


should_continue=1

while (should_continue == 1):


    for idx in range(ARGNO, NUMARGS):
        if (sys.argv[idx].find(":") == -1):
          #  http://46.103.116.66:8080/dump1090/data.json
          url = "http://" + sys.argv[idx] + ":8080/dump1090/data.json"
        else:
          url = "http://" + sys.argv[idx] + "/dump1090/data.json"

        try:
            #print "Reading url: {0}...".format(url)
            response = urllib2.urlopen(url)
            #print "URL opened..."
            #x = response.read()
            #print "Response read..."
            #d = json.loads(x)
            d = json.loads(response.read())
            #print "JSON data loaded."
        except:
            print '\n***Error reading URL: {0}'.format(url)
            d=''

        urlreceived = datetime.datetime.now()

        #print '\n'
        #print d
        #print 'Length of dictionary: %d\n' % len(d)
        #print '\n'

        ############# START OF PARSING ALL URL DATA  ###############
        for line in d:

            #print '\nRead line - %s' % line
            #for key in line:
            #   print 'key = %s   ' % key
            #   print 'value = %s\n' % line[key]

            # Initialize all displayable variables before reading new ones
            init_display_vars()

            # NOTE: Still have to fix CAOs that look like scientific notation (e.g. "780e08").  As of now they are
            #       being treated like actual hex strings and not numbers (e.g. "78000000000") and blowing the
            #       ICAO field's string formatting!
            #print '\nFORMATTED -'
            ICAO_HEX = line.get(KEY_ICAO, '').replace('~', '', 1)
            ICAO_STR = str(line.get(KEY_ICAO, '').encode('latin1')).upper()
            #print '\tICAO = %s' % ICAO
            CALLSIGN = str(line.get(KEY_CALLSIGN, '')).upper()
            #print '\tCALLSIGN = %s' % CALLSIGN
            LEVEL = line.get(KEY_LEVEL, NSN)
            #print '\tLEVEL = %s' % LEVEL
            GSPD = line.get(KEY_GSPD, NSN)
            #print '\tGSPD = %s' % GSPD
            TRACK = line.get(KEY_TRACK, NSN)
            #print '\tTRACK = %s' % TRACK
            LAT = line.get(KEY_LAT, NSN)
            #print '\tLAT = %s' % LAT
            LON = line.get(KEY_LON, NSN)
            #print '\tLON = %s' % LON
            VERT_RATE = line.get(KEY_VERT_RATE, NSN)
            #print '\tVERT_RATE = %s' % VERT_RATE
            SQUAWK= line.get(KEY_SQUAWK, NSN)
            #print '\tSQUAWK = %s' % SQUAWK
            RSSI = line.get(KEY_RSSI, NSN)
            #print '\tRSSI = %s' % RSSI
            AGE = line.get(KEY_AGE, NSN)
            #print '\tAGE = %s' % AGE
            VALID_POSITION = line.get(KEY_VALID_POSITION, 0)
            #print '\tVALID_POSITION = %s' % VALID_POSITION

            ############# END OF PARSING THIS PLANE's DATA ###############

            now=datetime.datetime.now()
            currdate=now.strftime('%Y/%m/%d')
            currtime=now.strftime('%H:%M:%S.{0}').format(now.microsecond)[0:12]

            # If AGE is NSN, treat it as if it were "zero"
            if (AGE == NSN):
                AGE=0
            then=urlreceived - datetime.timedelta(seconds=int(AGE))
            thendate=then.strftime('%Y/%m/%d')
            thentime=then.strftime('%H:%M:%S.{0}').format(now.microsecond)[0:12]

            if ((ICAO_HEX != NSN) & (CALLSIGN != '')):
                msg1="MSG,1,1,1,{0},1,{1},{2},{4},{5},{3},,,,,,,,,,,0\n".format(ICAO_HEX, thendate, thentime,CALLSIGN, currdate, currtime)
                q.put(msg1)
                if (GO_LIVE):
                    sys.stdout.write(msg1)

            if ((ICAO_HEX != NSN) & (LEVEL != NSN) & (LAT != NSN) & (LON != NSN) & (VALID_POSITION == 1)):
                msg3="MSG,3,1,1,{0},1,{1},{2},{6},{7},,{3},,,{4},{5},,,,,,0\n".format(ICAO_HEX, thendate, thentime,LEVEL,LAT,LON, currdate, currtime)
                q.put(msg3)
                if (GO_LIVE):
                    sys.stdout.write(msg3)

            if ((ICAO_HEX != NSN) & (GSPD != NSN) & (TRACK!= NSN) & (VERT_RATE != NSN) & (GSPD != 0) & (TRACK!= 0) & (VERT_RATE != 0)):
                msg4="MSG,4,1,1,{0},1,{1},{2},{6},{7},,,{3},{4},,,{5},,,,,0\n".format(ICAO_HEX,thendate,thentime,GSPD,TRACK,VERT_RATE,currdate,currtime)
                q.put(msg4)
                if (GO_LIVE):
                    sys.stdout.write(msg4)

        # Done, for this line from the URL

    # Done, for each IP address given on the command line

    time.sleep(SLEEP_INTERVAL)
    #should_continue=0

# End of while should_continue...


# Close socket
if (GO_LIVE):
    conn.close()
s.close()


raise SystemExit




#  VIRTUAL RADAR (ish) SERVER (calls itself "Server: Dump1090") -
#  http://46.103.116.66:8080/dump1090/data.json

#  FORMAT OF DATA -
#  [
#  {"hex":"4b1619", "squawk":"1755", "flight":"SWR255X ", "lat":40.591457, "lon":22.919603, "validposition":1, "altitude":2225,  "vert_rate":1152,"track":350, "validtrack":1,"speed":243, "messages":595, "seen":0},
#  {"hex":"4692d2", "squawk":"1753", "flight":"AEE5DL  ", "lat":40.740372, "lon":22.888367, "validposition":1, "altitude":9825,  "vert_rate":3008,"track":353, "validtrack":1,"speed":279, "messages":1262, "seen":0},
#  {"hex":"73806a", "squawk":"7253", "flight":"ELY381  ", "lat":40.889053, "lon":22.823181, "validposition":1, "altitude":35975,  "vert_rate":0,"track":317, "validtrack":1,"speed":454, "messages":760, "seen":0},
#  {"hex":"440910", "squawk":"7140", "flight":"", "lat":39.935256, "lon":21.309107, "validposition":1, "altitude":33000,  "vert_rate":128,"track":146, "validtrack":1,"speed":479, "messages":19, "seen":233},
#  {"hex":"4ac8ba", "squawk":"7443", "flight":"SAS7831 ", "lat":40.352142, "lon":22.438965, "validposition":1, "altitude":38975,  "vert_rate":-64,"track":152, "validtrack":1,"speed":484, "messages":693, "seen":0},
#  {"hex":"3c60d7", "squawk":"2064", "flight":"TUI1HB  ", "lat":40.697084, "lon":22.822723, "validposition":1, "altitude":36000,  "vert_rate":-64,"track":332, "validtrack":1,"speed":442, "messages":793, "seen":0},
#  {"hex":"400e4e", "squawk":"3403", "flight":"EXS743  ", "lat":40.395355, "lon":23.167908, "validposition":1, "altitude":37000,  "vert_rate":0,"track":135, "validtrack":1,"speed":468, "messages":479, "seen":61},
#  {"hex":"4071dd", "squawk":"4742", "flight":"EZY84EJ ", "lat":40.676102, "lon":22.633789, "validposition":1, "altitude":12625,  "vert_rate":-1408,"track":139, "validtrack":1,"speed":296, "messages":582, "seen":0},
#  {"hex":"4ba916", "squawk":"1367", "flight":"THY6AX  ", "lat":40.821099, "lon":23.641642, "validposition":1, "altitude":35000,  "vert_rate":0,"track":87, "validtrack":1,"speed":459, "messages":1046, "seen":40},
#  {"hex":"4ac8d9", "squawk":"7035", "flight":"BLX6A   ", "lat":39.833954, "lon":23.161867, "validposition":1, "altitude":39000,  "vert_rate":0,"track":164, "validtrack":1,"speed":468, "messages":1325, "seen":271},
#  {"hex":"44d076", "squawk":"7026", "flight":"CFG3LX  ", "lat":39.570147, "lon":23.276245, "validposition":1, "altitude":34975,  "vert_rate":0,"track":145, "validtrack":1,"speed":432, "messages":1224, "seen":60},
#  {"hex":"4408b1", "squawk":"7122", "flight":"EWG6640 ", "lat":39.779260, "lon":23.088379, "validposition":1, "altitude":37025,  "vert_rate":-64,"track":148, "validtrack":1,"speed":470, "messages":1315, "seen":184}
#  ]

