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
# DEFAULT TO 30 MINUTES?
max_age = (30.0*60.0)	# 30 mins - use for Production
#max_age = (24.0*60.0*60.0)	# Use for testing

# Age tolerance for alerting - Consider all alerts within this period to be "the same"
age_tolerance = (5*60)  # 5 minutes either way

# Re-check interval (in seconds)
recheck_interval = (60)

# Date that file was created
file_date = 0;

# Set to 1 if we should continuously refresh the display
continuous = 1


# How many time to re-home (vs redraw) the screen before
# clearing it out completely (don't clear every time, as
# it makes the screen "blink", which is annoying...)
LOOPS_BEFORE_CLS=6

# If a signal causes us to terminate, exit gracefully
def Exit_gracefully(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, Exit_gracefully)


signal.signal(signal.SIGINT, Exit_gracefully)


# The most recent aircraft signal-report file -
#aircraft_files = [ '/run/dump1090-fa/aircraft.json' ]
aircraft_files = glob.glob('/run/dump1090-fa/history*.json')
aircraft_files.append('/run/dump1090-fa/aircraft.json')


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



now = time.time()
print "\nTIME_NOW: ", now

max_age = now - max_age 
#print "\nMAX_AGE:  ", max_age, "\n"


met_criteria=0
total_aircraft=0
while met_criteria == 0:

  # Dictionary of all helicopter data
  helo_dict = {}

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

    # Pickup file-creation date
    file_date = data['now']
    #print "\nFile-creation date: ", file_date


    # Figure out how many aircraft are in this file
    num_found = len(data['aircraft'])

    #print "\nNumber of Aircraft found: ", num_found

    # Add aircraft from this file to total-found
    total_aircraft += num_found

    features = [ 'hex', 'flight', 'lat', 'lon', 'alt_baro' ]
    for i in range(0, num_found):
        if 'rssi' in data['aircraft'][i] \
and data['aircraft'][i]['rssi'] > -49.5 \
and 'seen' in data['aircraft'][i] \
and 'category' in data['aircraft'][i] \
and data['aircraft'][i]['category'] == "A7":

            seen = file_date - data['aircraft'][i]['seen']
            print "\nseen : ", seen,
            #age = now - seen
            age = seen
            print "\nage of siting: ", age,
            hex = data['aircraft'][i]['hex']

            if (age >= max_age) :

                # Create default position
                pos = {
                    'age': -9999999999,
                    'lat': 0,
                    'lon': 0,
                    'alt': 0
                }

                # Create default aircraft info
                aircraft = {
                    'hex': hex,
                    'oldest_age': 9999999999,
                    'newest_pos': pos,
                    'newest_age': -9999999999
                }

                # If hex is NOT in helo_dict
                if hex not in helo_dict.keys(): 
                    print "\n\nHelo ",hex, " Not present - adding it now...",
                    # Add default info to helo_dict
                    helo_dict[hex] = aircraft
                else: 
                    print "\n\nHelo ",hex, " already present",

                print "\n", age,
                met_criteria += 1
                for feature in features:
	            if feature in data['aircraft'][i]:
	                print " ", feature, ": ", data['aircraft'][i][feature],
	            else:
	                print " ", feature, ": ", " unk ",


                # Keep oldest age for hex
                if age < helo_dict[hex]['oldest_age']:
                    print "\nFound older age of: ",age
                    helo_dict[hex].update({'oldest_age': age})


                # Keep newest lat/long/alt for hex
                if 'lat' in data['aircraft'][i] \
and 'lon' in data['aircraft'][i] \
and 'alt_baro' in data['aircraft'][i] \
and age > helo_dict[hex]['newest_pos']['age']:

                    print "\nFound newer position with age of: ",age
                    helo_dict[hex]['newest_pos'].update({
                        'age': age,
                        'lat': data['aircraft'][i]['lat'],
                        'lon': data['aircraft'][i]['lon'],
                        'alt': data['aircraft'][i]['alt_baro']
                    })


                # keep newest age for hex
                if age > helo_dict[hex]['newest_age']:
                    print "\nFound newer age of: ",age
                    helo_dict[hex].update({'newest_age': age})



            # End, sighting is recent enough to be considered

    # End, processing of this one file is complete

  # End, processing of all aircraft files are complete

  # Done looking through all aircraft for candidates

  print "\n"
  pprint(helo_dict)

  # Look through helo_dict
  # For each entry in helo_dict
  for key in helo_dict.keys():
      # If newest_age > oldest_age:
      if helo_dict[key]['newest_age'] > (helo_dict[key]['oldest_age'] - age_tolerance):
          # This sighting is new. See if it's recent enough to alert on
          if helo_dict[key]['newest_age'] > (now - age_tolerance):
              print "\n\t**** ALERT: NEW HELO: ",key
          else:
              print "\n\t     New, but already-alerted on helo: ",key
      else:
          # We've seen this aircraft before. Don't alert on it
          print "\n\t      Re-sighting of: ",key

          '''
{u'a8aa7e': {'hex': u'a8aa7e',
             'newest_age': 2099.9381449222565,
             'newest_pos': {'age': 2099.9381449222565,
                            'alt': u'ground',
                            'lat': 34.587994,
                            'lon': -117.375309},
             'oldest_age': 2947.838145017624}}
          '''


  print '\n%s GMT     Aircraft: %d/%d      ' % (time.asctime(time.gmtime()), met_criteria,total_aircraft)


  print ""

  if continuous == 1:
    met_criteria=0
    total_aircraft=0
    sys.stdout.flush()
    time.sleep(recheck_interval)

  else:
    quit()


raise SystemExit


#
# aircraft.json is MAIN (current) FILE
#
# HISTORICAL FILES -
#
#  1) Stored in $DATADIR/history_[0-99999].json
#  3) Seem to be created in 30-second intervals
#  4) The first line of each file has a seconds-since-epoch (UTC) in the JSON attribute "now", with one digit of decimal precision
#  5) Attribute "category" of "A7" is known to be a helicopter
#  6) Others in category "A1" have been helicopters, but can't tell how FlightAware knows this - perhaps by tail number/registration database
#
# EXAMPLE aircraft.json FILE -
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




'''

EXAMPLE OUTPUT (so far) -

2533.80363703   hex :  a8aa7e   flight :  N658AM     lat :  34.543304   lon :  -117.264535   alt_baro :  2700
2533.80363703   hex :  a8aa7e   flight :  N658AM     lat :  34.543304   lon :  -117.264535   alt_baro :  2700
2533.80363679   hex :  a8aa7e   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
2533.80363679   hex :  a8aa7e   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
2533.80363679   hex :  a8aa7e   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
2533.80363679   hex :  a8aa7e   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
2533.70363688   hex :  a8aa7e   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
1014.00363684   hex :  a0ca3b   flight :  N150AM     lat :  34.166922   lon :  -117.045422   alt_baro :  7500
983.903636932   hex :  a0ca3b   flight :  N150AM     lat :  34.175534   lon :  -117.031059   alt_baro :  7600
954.10363698   hex :  a0ca3b   flight :  N150AM     lat :  34.185883   lon :  -117.015381   alt_baro :  8000
923.803637028   hex :  a0ca3b   flight :  N150AM     lat :  34.195816   lon :  -116.999686   alt_baro :  8200
893.903636932   hex :  a0ca3b   flight :  N150AM     lat :  34.206161   lon :  -116.985   alt_baro :  8500
874.503637075   hex :  a0ca3b   flight :  N150AM     lat :  34.212891   lon :  -116.975415   alt_baro :  8600
841.903636932   hex :  a0ca3b   flight :  N150AM     lat :  34.221268   lon :  -116.958992   alt_baro :  8500
804.403636932   hex :  a0ca3b   flight :  N150AM     lat :  34.233398   lon :  -116.930573   alt_baro :  7900
780.403636932   hex :  a0ca3b   flight :   unk    lat :  34.242057   lon :  -116.913757   alt_baro :  7600
756.703637123   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703637123   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703636885   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703636885   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703636885   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703636885   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703636885   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
756.703636885   hex :  a0ca3b   flight :   unk    lat :  34.242057   lon :  -116.913757   alt_baro :  7600
756.703636885   hex :  a0ca3b   flight :   unk    lat :  34.242057   lon :  -116.913757   alt_baro :  7600
756.603636742   hex :  a0ca3b   flight :   unk    lat :   unk    lon :   unk    alt_baro :   unk
533.60363698   hex :  a8aa7e   flight :  N658AM     lat :  34.538222   lon :  -117.265778   alt_baro :  3100
503.503637075   hex :  a8aa7e   flight :  N658AM     lat :  34.527145   lon :  -117.26958   alt_baro :  3600
473.503637075   hex :  a8aa7e   flight :  N658AM     lat :  34.513367   lon :  -117.272046   alt_baro :  4100
443.403636932   hex :  a8aa7e   flight :  N658AM     lat :  34.498077   lon :  -117.271486   alt_baro :  4600
413.303636789   hex :  a8aa7e   flight :  N658AM     lat :  34.48222   lon :  -117.271786   alt_baro :  5100
383.403636932   hex :  a8aa7e   flight :  N658AM     lat :  34.46553   lon :  -117.271542   alt_baro :  5600
353.303637028   hex :  a8aa7e   flight :  N658AM     lat :  34.448796   lon :  -117.271156   alt_baro :  6100
323.203636885   hex :  a8aa7e   flight :  N658AM     lat :  34.428964   lon :  -117.27047   alt_baro :  6100
293.303637028   hex :  a8aa7e   flight :  N658AM     lat :  34.408621   lon :  -117.270184   alt_baro :  6100
263.203636885   hex :  a8aa7e   flight :  N658AM     lat :  34.387998   lon :  -117.269955   alt_baro :  6100
233.103636742   hex :  a8aa7e   flight :  N658AM     lat :  34.367432   lon :  -117.269804   alt_baro :  6100
203.003636837   hex :  a8aa7e   flight :  N658AM     lat :  34.347079   lon :  -117.269039   alt_baro :  6100
173.003636837   hex :  a8aa7e   flight :  N658AM     lat :  34.326508   lon :  -117.268907   alt_baro :  6100
143.003636837   hex :  a8aa7e   flight :  N658AM     lat :  34.305862   lon :  -117.268571   alt_baro :  6200
112.903636932   hex :  a8aa7e   flight :  N658AM     lat :  34.284978   lon :  -117.268124   alt_baro :  6200
82.8036370277   hex :  a8aa7e   flight :  N658AM     lat :  34.263983   lon :  -117.267838   alt_baro :  6200
52.8036370277   hex :  a8aa7e   flight :  N658AM     lat :  34.243593   lon :  -117.267494   alt_baro :  6200
23.4036369324   hex :  a8aa7e   flight :  N658AM     lat :  34.223343   lon :  -117.267036   alt_baro :  6200
0.30363702774   hex :  a8aa7e   flight :  N658AM     lat :  34.207581   lon :  -117.266609   alt_baro :  6100


* Filter data that is older than max_age (say, 30 minutes)
* Use hex as key to create a per-aircraft table
* Keep the most recent "valid" lat/long/alt data in per-aircraft table (using hex as key)
* Keep all heard-timestamps in per-aircraft table (using hex as key)

Keep oldest age for hex
Keep newest lat/long/alt for hex
keep newest age for hex

'''
