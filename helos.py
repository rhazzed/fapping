#! /usr/bin/python
############################################
# helos.py - An alert tool to identify when helicopters (helos) appear and disappear from your PiAware radar screen
#
# HISTORICAL INFORMATION -
#
#  2017-04-28  msipin  Derived from the 2020-10-09 version of fap.py
############################################

import sys
import json
from pprint import pprint
import glob
import time
import subprocess as sp
import signal


##   DATADIR ="/run/dump1090-fa"
##   CURRDATA ="${DATADIR}/aircraft.json"


# (Approx.) Miles-per-degree of latitude/longitude - accuracy is
# not as important; only being used for rough estimation for visual
# graphing purposes.
mpd_lat = 69.0535	# Avg, equator-to-pole
mpd_lon = 53.0000	# At 40 degrees N/S

# How old (in seconds) a reading can be before we consider
# it no longer valid for our purposes
#
# DEFAULT TO 10 MINUTES?
max_age = (10*60.0)


# Distance (in miles) to divide display into (left-right, and up-down)
graph_width = 300	# Distance in miles (I personally like 300 miles!)
graph_height = 300	# Distance in miles (I personally like 300 miles!)

# Set to 1 if we should display the altitude indicators
show_altitude = 1

# Set to 1 if we should continuously refresh the display
continuous = 0


# How many time to re-home (vs redraw) the screen before
# clearing it out completely (don't clear every time, as
# it makes the screen "blink", which is annoying...)
LOOPS_BEFORE_CLS=6

lcount=LOOPS_BEFORE_CLS

# If a signal causes us to terminate, exit gracefully
def Exit_gracefully(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, Exit_gracefully)


signal.signal(signal.SIGINT, Exit_gracefully)



# The most recent aircraft signal-report file -
aircraft_files = [ '/run/dump1090-fa/aircraft.json' ]


# Get position of receiver ("site")
site_file = '/run/dump1090-fa/receiver.json'
site_data=open(site_file)
site = json.load(site_data)
#pprint(site)
site_data.close()

#print ""

# If we don't know where receiver is, we can't continue, so - exit.
if 'lat' in site and 'lon' in site:
    site_lat = site['lat']
    #print "Site Latitude: ", site_lat
    site_lon = site['lon']
    #print "Site Longitude: ", site_lon
else:
    print "\nERROR: Site's position is unknown.  Can not continue.\n"
    raise SystemExit



met_criteria=0
total_aircraft=0
while met_criteria == 0:
  for aircraft_file in aircraft_files:

    # If we are looping in "continuous" mode, clear out the grid
    # BUG BUG BUG:
    # BUG BUG BUG: The logic below fails if we ever want to repeatedly generate
    #              this plot *AND* are using multiple files to do so. MUST change
    #              this logic if ever we want to BOTH repeatedly generate the
    #              plot *AND* we are using multiple files to do so.
    # BUG BUG BUG:

    aircraft_data=open(aircraft_file)
    data = json.load(aircraft_data)
    #pprint(data)
    aircraft_data.close()

    # Figure out how many aircraft are in this file
    num_found = len(data['aircraft'])

    print "\nNumber of Aircraft parsed: ", num_found

    # Add aircraft from this file to total-found
    total_aircraft += num_found

    features = ['hex', 'flight', 'seen', 'lat', 'lon', 'alt_baro', 'category' ]
    for i in range(0, num_found):
        if 'rssi' in data['aircraft'][i] \
and data['aircraft'][i]['rssi'] > -49.5 \
and 'seen' in data['aircraft'][i] \
and 'lat' in data['aircraft'][i] \
and 'lon' in data['aircraft'][i] \
and 'category' in data['aircraft'][i] \
and data['aircraft'][i]['category'] == "A7" \
and data['aircraft'][i]['seen'] <= max_age:
            print "\nAircraft[", i, "] - "
            met_criteria += 1
            for feature in features:
	        if feature in data['aircraft'][i]:
	            print "    ", feature, ": ", data['aircraft'][i][feature]

	    # longitude
	    lon = data['aircraft'][i]['lon']

	    # latitude
	    lat = data['aircraft'][i]['lat']

	    # altitude
	    if 'alt_baro' in data['aircraft'][i]:
	        alt = data['aircraft'][i]['alt_baro']
	
    # End, processing of this one file is complete

  # End, processing of all aircraft files are complete


  # Done looking through all aircraft for candidates

  #print '\n%s GMT     Aircraft: %d/%d      ' % (time.asctime(time.gmtime()), met_criteria,total_aircraft)


  print ""

  if continuous == 1:
    met_criteria=0
    total_aircraft=0
    sys.stdout.flush()
    time.sleep(4)
    lcount = lcount -1
    if lcount <= 1:
        sp.call('tput clear',shell=True)
        lcount=LOOPS_BEFORE_CLS
    else:
        sp.call('tput home',shell=True)

  else:
    quit()


raise SystemExit


#
# HISTORICAL FILES -
#
#  1) Stored in $DATADIR/history_[0-99999].json
#  2) Lower number earlier in time
#  3) Seem to be created in 30-second intervals
#  4) If "3" is true, 10 minutes would constitute the current (aircraft.json) and previous 19 "history_xxx.json" files
#  5) The first line of each file has a seconds-since-epoch (UTC) in the JSON attribute "now", with one digit of decimal precision
#  6) Attribute "category" of "A7" is known to be a helicopter
#  7) Others in category "A1" have been helicopters, but can't tell how FlightAware knows this - perhaps by tail number/registration database
#
#
#
# EXAMPLE FILE -
#
#  { "now" : 1602919584.1,
#    "messages" : 337172772,
#    "aircraft" : [
#      {"hex":"a76f46","flight":"UAL584  ","alt_baro":26500,"alt_geom":27900,"gs":453.3,"track":50.6,"baro_rate":1408,"squawk":"7363","emergency":"none","category":"A4","nav_qnh":1013.6,"nav_altitude_mcp":35008,"nav_heading":38.7,"lat":34.297222,"lon":-117.468910,"nic":8,"rc":186,"seen_pos":0.4,"version":2,"nic_baro":1,"nac_p":9,"nac_v":1,"sil":3,"sil_type":"perhour","gva":2,"sda":2,"mlat":[],"tisb":[],"messages":3767,"seen":0.4,"rssi":-4.8},
#      
#      {"hex":"ac9e77","flight":"DAL1106 ","alt_baro":37000,"alt_geom":38650,"gs":496.2,"track":108.7,"baro_rate":-64,"squawk":"3345","emergency":"none","category":"A3","nav_qnh":1013.6,"nav_altitude_mcp":36992,"nav_heading":94.9,"lat":38.015907,"lon":-116.142684,"nic":8,"rc":186,"seen_pos":17.8,"version":2,"nic_baro":1,"nac_p":9,"nac_v":1,"sil":3,"sil_type":"perhour","gva":2,"sda":2,"mlat":[],"tisb":[],"messages":601,"seen":14.3,"rssi":-20.1},
#      
# HELICOPTER IN NEXT LINE -
#      {"hex":"a8aa7e","flight":"N658AM  ","alt_baro":"ground","gs":0.0,"track":278.4,"squawk":"1200","emergency":"none","category":"A7","lat":34.587987,"lon":-117.375355,"nic":9,"rc":75,"seen_pos":27.9,"version":2,"nac_p":10,"nac_v":2,"sil":3,"sil_type":"perhour","sda":2,"mlat":[],"tisb":[],"messages":5272,"seen":27.9,"rssi":-19.2},

