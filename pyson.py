#! /usr/bin/python
############################################
# pyson.py - A Python script to extract real-time ADS-B aircraft beacon data from a PiAware
#
# HISTORICAL INFORMATION -
#
#  2017-05-31  msipin  Created.
############################################

import sys
import urllib, json


# "No Such Number" - Until I can figure out how to filter out non-existent dictionary entries,
# this will be my signal that a dictionary had no value at a given key
NSN=424242424242

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


print "\n  ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK |RSSI       "

url = "http://192.168.2.127:8080/aircraft.json"
response = urllib.urlopen(url)
d = json.loads(response.read())['aircraft']
#print '\n'
#print d
#print 'Length of dictionary: %d\n' % len(d)
#print '\n'
for line in d:
    #print '\nRead line - %s' % line
    #for key in line:
    #   print 'key = %s   ' % key
    #   print 'value = %s\n' % line[key]


    #print '\nFORMATTED -'
    ICAO = str(line.get(KEY_ICAO, '')).upper()
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

    #print "%7s|%8s|%6s|%4s|%4s|%11s|%11s|%6s|%5s|%6s" % '{:7s}'.format(ICAO), '{:8s}'.format(CALLSIGN), '{:6s}'.format(LEVEL), '{:4s}'.format(GSPD), '{:4s}'.format(TRACK), '{:11s}'.format(LAT), '{:6s}'.format(LON), '{:5s}'.format(VERT_RATE), '{:6s}'.format(SQUAWK), '{:xs}'.format(RSSI)
    sys.stdout.write('{:7s}'.format(ICAO))
    sys.stdout.write('|')
    sys.stdout.write('{:8s}'.format(CALLSIGN))
    sys.stdout.write('|')
    if (LEVEL != NSN):
        sys.stdout.write('{:6d}'.format(LEVEL))
    else:
        sys.stdout.write('{:6s}'.format(''))
    sys.stdout.write('|')
    if (GSPD!= NSN):
        sys.stdout.write('{:4d}'.format(GSPD))
    else:
        sys.stdout.write('{:4s}'.format(''))
    sys.stdout.write('|')
    if (TRACK != NSN):
        sys.stdout.write('{:4d}'.format(TRACK))
    else:
        sys.stdout.write('{:4s}'.format(''))
    sys.stdout.write('|')

    # TO-DO: CONVERT LAT+LONG into RANGE (nm)
    #sys.stdout.write('{:4d}'.format(RANGE))
    sys.stdout.write('{:-6.1f}'.format(999.9))

    sys.stdout.write('|')
    if (VERT_RATE != NSN):
        sys.stdout.write('{:6d}'.format(VERT_RATE))
    else:
        sys.stdout.write('{:6s}'.format(''))
    sys.stdout.write('|')
    if (SQUAWK != NSN):
        sys.stdout.write('{:5s}'.format(SQUAWK))
    else:
        sys.stdout.write('{:5s}'.format(''))
    sys.stdout.write('|')
    if (RSSI != NSN):
        sys.stdout.write('{:-2.1f}'.format(RSSI))
    else:
        sys.stdout.write('{:i6s}'.format(''))

    sys.stdout.write('\n')

    #instr = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9}".format(ICAO, CALLSIGN, LEVEL, GSPD, TRACK, LAT, LON, VERT_RATE, SQUAWK, RSSI)
    #print instr

#   ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK |RSSI       ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK |RSSI  
#   if (NR > 1) printf "%7s|%8s|%6s|%4s|%4s|%6.1f|%6s|%5s|%6s", toupper(ICAO), CALLSIGN, LEVEL, GSPD, TRACK, RANGE, VERT_RATE, SQUAWK, RSSI
# if ($1 == "flight") CALLSIGN=$2



raise SystemExit


#########################
# Potentially useful URLs  -
# 
# http://192.168.2.117:8080/receiver.json
# { "version" : "3.5.0", "refresh" : 1000, "history" : 120, "lat" : 34.492610, "lon" : -117.407060 }
# 
# 
# http://192.168.2.117:8080/aircraft.json
# { "now" : 1496279916.6,
#  "messages" : 420047,
#  "aircraft" : [
#    {"hex":"a76fe9","altitude":23000,"mlat":[],"tisb":[],"messages":2,"seen":0.2,"rssi":-9.5},
#    {"hex":"ab0d15","squawk":"2023","flight":"AAL2576 ","lat":34.385605,"lon":-117.692497,"nucp":7,"seen_pos":0.4,"altitude":28700,"vert_rate":2112,"track":50,"speed":478,"category":"A5","mlat":[],"tisb":[],"messages":381,"seen":0.0,"rssi":-2.4},
#    {"hex":"a260bc","altitude":10150,"mlat":[],"tisb":[],"messages":77,"seen":18.0,"rssi":-3.7},
#    {"hex":"a9d7c1","squawk":"6736","altitude":33350,"mlat":[],"tisb":[],"messages":635,"seen":0.3,"rssi":-2.5},
#    {"hex":"ac3456","squawk":"4674","flight":"N886CE  ","lat":34.730118,"lon":-117.480562,"nucp":7,"seen_pos":0.0,"altitude":19175,"vert_rate":-1728,"track":257,"speed":390,"category":"A2","mlat":[],"tisb":[],"messages":730,"seen":0.0,"rssi":-3.7},
#    {"hex":"a24082","mlat":[],"tisb":[],"messages":10,"seen":276.7,"rssi":-3.7},
#    {"hex":"c06e87","squawk":"1022","altitude":28825,"mlat":[],"tisb":[],"messages":1203,"seen":0.1,"rssi":-2.6},
#    {"hex":"a1f1de","altitude":29000,"mlat":[],"tisb":[],"messages":1934,"seen":46.9,"rssi":-4.3},
#    {"hex":"a47fd9","mlat":[],"tisb":[],"messages":1755,"seen":145.8,"rssi":-4.3},
#    {"hex":"a50f40","altitude":14950,"mlat":[],"tisb":[],"messages":902,"seen":56.5,"rssi":-3.9},
#    {"hex":"a9a90b","mlat":[],"tisb":[],"messages":1608,"seen":98.9,"rssi":-4.6},
#    {"hex":"a72c3b","mlat":[],"tisb":[],"messages":1607,"seen":97.3,"rssi":-4.3},
#    {"hex":"~adf9c2","type":"adsb_other","mlat":[],"tisb":[],"messages":8101,"seen":1.0,"rssi":-3.7}
#  ]
#}
#
