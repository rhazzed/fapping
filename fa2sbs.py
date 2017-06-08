#! /usr/bin/python
############################################
# fa2sbs.py - A Python program to extract real-time ADS-B aircraft beacon data from one or more
#             FlightAware "aircraft.json" URLs and produce SBS-1 BaseStation records from them.
#
# HISTORICAL INFORMATION -
#
#  2017-06-05  msipin  Derived from pyson.py.
#  2017-06-06  msipin  Added command-line specification of server port number.
############################################

import sys
import math
import urllib
import json
import time
import datetime
import socket
import sys
import Queue
import threading



HOST = ''  # Symbolic name meaning all available interfaces
#PORT = 3003  # Arbitrary non-privileged port




# "No Such Number" - Until I can figure out how to filter out non-existent dictionary entries,
# this will be my signal that a dictionary had no value at a given key
NSN=424242424242

# JSON field names - as defined by PiAware's read-from-airplane-data-URL functionality
KEY_ICAO='hex'
KEY_CALLSIGN='flight'
KEY_LEVEL='altitude'
KEY_GSPD='speed'
KEY_TRACK='track'
KEY_LAT='lat'
KEY_LON='lon'
KEY_VERT_RATE='vert_rate'
KEY_SQUAWK='squawk'
KEY_RSSI='rssi'
KEY_AGE='seen'

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

# How old (in seconds) a reading can be before we consider
# it no longer valid for display purposes
max_age = 120

# How old (in seconds) an aircraft data db entry can be before
# we completely remove it from the database
#TOO_DARN_OLD=60	# TEST VALUE!
#TOO_DARN_OLD=120	# TEST VALUE!
TOO_DARN_OLD=22500	# (NOTE: 22500 = 6.25 hours) - This is arbitrary, but was
			# developed by calculating how long it would take a UAV that
			# was flying at 80 mph to cross a 500 mile wide receiver
			# field-of-view.  (Why? Because... science!....not)

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



def _calc_range_in_miles(from_lat, from_lon, to_lat, to_lon):

    # TO-DO: Calculate this range value using "real" Great Circle maths

    global NSN

    # (Approx.) Miles-per-degree of latitude/longitude - accuracy is
    # not as important; only being used for rough estimation
    # of RANGE, and for comparison in sort operations
    mpd_lat = 69.0535  # Avg, equator-to-pole
    mpd_lon = 53.0000  # At 40 degrees N/S

    # CONVERT LAT+LONG into RANGE in miles
    range = NSN
    if ((from_lat != NSN) & (from_lon != NSN) & (to_lat != NSN) & (to_lon != NSN)):
       dlat = from_lat - to_lat
       # Calculate approximate distance (in miles) of delta in latitude
       lat_delta_miles = dlat * mpd_lat

       dlon = from_lon - to_lon
       # Calculate approximate distance (in miles) of delta in longitude
       lon_delta_miles = dlon * mpd_lon

       # Calculate the approximate range (in nautical miles)
       range = math.sqrt((lat_delta_miles * lat_delta_miles) + (lon_delta_miles * lon_delta_miles))

    return range



def _calc_range_in_nm(from_lat, from_lon, to_lat, to_lon):

    global NSN

    range = NSN
    range = _calc_range_in_miles(from_lat, from_lon, to_lat, to_lon)
    if (range != NSN):
        range = range * 0.868976    # 1 Mile is 0.868976 Nautical Miles
    return range



def get_key(q,conn):
    while 1:
        # Block on any data arriving in the queue
        indata = q.get()
        # Write that data to socket
        conn.sendall(indata)








if (len(sys.argv) <3):
    sys.stderr.write('\nusage: {0} <server_port_number> <ip_address[:port]> [<ip_address2[:port]>...]\n\n'.format(sys.argv[0]))
    sys.stderr.write("server_port_number is required. This is where the program will serve up the data it retrieves.\n")
    sys.stderr.write("At least one IP address is required.\n")
    sys.stderr.write("Port number for any IP address is optional, with a default of 8080.\n")
    sys.stderr.write("If more than one IP address is provided, all range calculations will be based\n")
    sys.stderr.write("upon the location of the receiver at the first IP address provided.\n\n")
    raise SystemExit

# Pick up Server Port Number
PORT=int(sys.argv[1])

# Pickup IP address
NUMARGS=len(sys.argv)
ARGNO=2





# Pickup receiver lat/lon from the FIRST (and possibly only) IP address given on the command line
# { "version" : "3.5.0", "refresh" : 1000, "history" : 120, "lat" : 32.1219, "lon" : -38.854451 }
if (sys.argv[ARGNO].find(":") == -1):
    url = "http://" + sys.argv[ARGNO] + ":8080/dump1090-fa/data/receiver.json"
else:
    url = "http://" + sys.argv[ARGNO] + "/dump1090-fa/data/receiver.json"
response = urllib.urlopen(url)
line = json.loads(response.read())
RX_LAT = line.get(KEY_LAT, NSN)
#print '\tRX_LAT = %s' % RX_LAT
RX_LON = line.get(KEY_LON, NSN)
#print '\tRX_LON = %s' % RX_LON

if ((RX_LAT == NSN) | (RX_LON == NSN)):
    print '\nERROR: Receiver location unknown.\nExiting!'
    raise SystemExit




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

# wait to accept a connection - blocking call
conn, addr = s.accept()
print 'Connected with ' + addr[0] + ':' + str(addr[1])


# Start the socket-handling thread
q = Queue.Queue()
t = threading.Thread(target=get_key, args = (q,conn))
t.daemon = True
t.start()


should_continue=1


while (should_continue == 1):


    for idx in range(ARGNO, NUMARGS):
        if (sys.argv[idx].find(":") == -1):
          url = "http://" + sys.argv[idx] + ":8080/dump1090-fa/data/aircraft.json"
        else:
          url = "http://" + sys.argv[idx] + "/dump1090-fa/data/aircraft.json"

        response = urllib.urlopen(url)
        d = json.loads(response.read())['aircraft']
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

            ############# END OF PARSING THIS PLANE's DATA ###############

            now=datetime.datetime.now()
            currdate=now.strftime('%Y/%m/%d')
            currtime=now.strftime('%H:%M:%S.{0}').format(now.microsecond)[0:12]

            if ((ICAO_HEX != NSN) & (CALLSIGN != '')):
                msg1="MSG,1,1,1,{0},1,{1},{2},{1},{2},{3},,,,,,,,,,,0\n".format(ICAO_HEX, currdate, currtime,CALLSIGN)
                sys.stdout.write(msg1)
                q.put(msg1)

            if ((ICAO_HEX != NSN) & (LEVEL != NSN) & (LAT != NSN) & (LON != NSN)):
                msg3="MSG,3,1,1,{0},1,{1},{2},{1},{2},,{3},,,{4},{5},,,,,,0\n".format(ICAO_HEX, currdate, currtime,LEVEL,LAT,LON)
                sys.stdout.write(msg3)
                q.put(msg3)

            if ((ICAO_HEX != NSN) & (GSPD != NSN) & (TRACK!= NSN) & (VERT_RATE != NSN)):
                msg4="MSG,4,1,1,{0},1,{1},{2},{1},{2},,,{3},{4},,,{5},,,,,0\n".format(ICAO_HEX,currdate,currtime,GSPD,TRACK,VERT_RATE)
                sys.stdout.write(msg4)
                q.put(msg4)

        # Done, for this line from the URL

    # Done, for each IP address given on the command line

    time.sleep(SLEEP_INTERVAL)

# End of while should_continue...


# Close socket
conn.close()
s.close()


raise SystemExit



# print "MSG,3,1,1,<ICAO>,1,date_gen  ,time_gen    ,date_logd ,time_logged ,,<ALT>,,,<LAT>,<LON>,,,,,,0"
#      MSG,3,1,1,A4D9A7,1,2017/06/06,01:50:29.537,2017/06/06,01:50:29.591,,10000,,,34.29584,-117.34615,,,,,,0
#      MSG,3,1,1,3C4B04,1,2017/06/06,01:50:30.143,2017/06/06,01:50:30.192,,29850,,,35.32915,-116.18580,,,,,,0
#      MSG,3,1,1,A1013A,1,2017/06/06,01:50:30.155,2017/06/06,01:50:30.193,,4900,,,34.70975,-118.20028,,,,,,
#      MSG,3,1,1,AA7E79,1,2017/06/06,01:50:30.157,2017/06/06,01:50:30.193,,33000,,,35.16589,-120.26711,,,,,,0
#      MSG,3,1,1,AB20C0,1,2017/06/06,01:50:30.157,2017/06/06,01:50:30.193,,20000,,,35.62652,-119.88001,,,,,,0
#      MSG,3,1,1,406D4C,1,2017/06/06,01:50:30.178,2017/06/06,01:50:30.196,,22875,,,34.25388,-117.53305,,,,,,0
#      MSG,3,1,1,A1D873,1,2017/06/06,01:50:30.213,2017/06/06,01:50:30.249,,28950,,,33.49841,-116.77560,,,,,,0
#      MSG,3,1,1,AA7734,1,2017/06/06,01:50:30.239,2017/06/06,01:50:30.252,,26125,,,34.37403,-119.31971,,,,,,0
#      MSG,3,1,1,A34209,1,2017/06/06,01:50:30.251,2017/06/06,01:50:30.301,,38000,,,37.98505,-117.94466,,,,,,0

# print "MSG,4,1,1,<ICAO>,1,date_gen  ,time_gen    ,date_logd ,time_logged ,,,<GSPD>,<TRK>,,,<VERT_RATE>,,,,,0"
#      MSG,4,1,1,AA3417,1,2017/06/06,01:50:29.557,2017/06/06,01:50:29.593,,,516,52,,,1152,,,,,0
#      MSG,4,1,1,A4BC10,1,2017/06/06,01:50:30.136,2017/06/06,01:50:30.191,,,439,316,,,1024,,,,,0
#      MSG,4,1,1,ACB1E5,1,2017/06/06,01:50:30.143,2017/06/06,01:50:30.192,,,376,238,,,-1024,,,,,0
#      MSG,4,1,1,3C4B04,1,2017/06/06,01:50:30.143,2017/06/06,01:50:30.192,,,524,48,,,1024,,,,,0
#      MSG,4,1,1,A83988,1,2017/06/06,01:50:30.146,2017/06/06,01:50:30.192,,,467,133,,,-960,,,,,0
#      MSG,4,1,1,AB77EE,1,2017/06/06,01:50:30.147,2017/06/06,01:50:30.192,,,364,245,,,-896,,,,,0
#      MSG,4,1,1,A3E6C9,1,2017/06/06,01:50:30.148,2017/06/06,01:50:30.192,,,291,168,,,0,,,,,0
#      MSG,4,1,1,A4D9A7,1,2017/06/06,01:50:30.177,2017/06/06,01:50:30.196,,,286,137,,,-1024,,,,,0
#      MSG,4,1,1,406D4C,1,2017/06/06,01:50:30.179,2017/06/06,01:50:30.196,,,503,51,,,1280,,,,,0
#      MSG,4,1,1,A9D5DF,1,2017/06/06,01:50:30.190,2017/06/06,01:50:30.197,,,516,59,,,576,,,,,0
#      MSG,4,1,1,AD9E4D,1,2017/06/06,01:50:30.218,2017/06/06,01:50:30.249,,,453,245,,,-1664,,,,,0
#      MSG,4,1,1,A46CE1,1,2017/06/06,01:50:30.219,2017/06/06,01:50:30.249,,,407,282,,,0,,,,,0
#      MSG,4,1,1,48AE01,1,2017/06/06,01:50:30.239,2017/06/06,01:50:30.252,,,408,228,,,-896,,,,,0


# now keep talking with the client
while 1:
    # wait to accept a connection - blocking call
    conn, addr = s.accept()
    print 'Connected with ' + addr[0] + ':' + str(addr[1])

    data = conn.recv(1024)
    reply = 'OK...' + data
    if not data:
        break

    conn.sendall(reply)

conn.close()
s.close()
