#! /usr/bin/python
############################################
# fap.py - A Python script to extract real-time ADS-B aircraft beacon data from the PiAware
#          script output and display signal-strength, location and altitude from the perspective
#          of the receiver.
#
# HISTORICAL INFORMATION -
#
#  2017-04-28  msipin  Created.
#  2017-04-30  msipin  Stopped displaying the highest altitude of any plane in a given grid, and
#                      instead only show the altitude of the plane that has the strongest signal.
#  2017-04-30  epowell Added colors to display for weakest (red) and strongest (green) signals,
#                      and lowest (red) and highest (green) altitudes. NOTE: If using the "watch"
#                      command, add the argument "--color" to preserve these colors on screen.
#  2017-05-01  epowell Added ability to continuously update the display ("-c") -- use <Ctrl>-C to
#                      break out of this.
#  2017-05-01  msipin  Added ability to use ALL signal history ("-a").
#  2017-05-03  msipin  Increased grid size when using all ("-a") received signal history. This
#                      should allow user to better see the edges of the grid, and infer both the
#                      dynamic range and rolloff of their receiver/site.
#  2017-05-04  epowell Added a new color scheme for displaying signal-strength when showing all
#                      history ("-a").  Added Plot and Grid size indicators.
#  2017-05-04  msipin  Reduced "S0" signal threshold from -30db to -33db. Increased last-received
#                      duration from 10 to 15 seconds.  Tidied up headers and footers. Added date
#                      and timestamp to display. Removed need for aircraft to have a "track"
#                      attribute.
#  2017-05-04  msipin  Displayed total number of aircraft that were in the signal source(s).
#  2017-05-15  msipin  Cleared out the screen "every once in a while" (vs just moving the cursor
#                      to "home" (top-left of screen). Better-formatted header and footer information.
#  2017-05-21  msipin  Changed "all" plot grid to 500x500 miles.
############################################

import sys
import json
from pprint import pprint
import glob
import time
import subprocess as sp
import signal

# (Approx.) Miles-per-degree of latitude/longitude - accuracy is
# not as important; only being used for rough estimation for visual
# graphing purposes.
mpd_lat = 69.0535	# Avg, equator-to-pole
mpd_lon = 53.0000	# At 40 degrees N/S

# How old (in seconds) a reading can be before we consider
# it no longer valid for our purposes
max_age = 15.0


# Signal Strength as a character, '9' = excellent, '1' = bad
rssi_chars = ['9','9','8','8','8','7','7','7','6','6','6','5','5', \
'5','4','4','4','3','3','3','2','2','2','1','1','1' ]
rss_min = -33.0	# Minumum RSSI for "bucketing" purposes
rss_max = -6.0		# Maximum RSSI for "bucketing" purposes
rss_buckets = 26	# NOTE: THIS *MUST* MATCH the rssi_chars array size!

# Delta-per-bucket for RSSI
rss_bd = (rss_min - rss_max)/rss_buckets

# Altitude as a character, '+' is >= 40,000 ft, A-J is down from there, where J is <= 1,000 ft
alt_chrs = [ 'J','I','H','G','F','E','D','C','B','A','+']


# Distance (in miles) to divide display into (left-right, and up-down)
graph_width = 300	# Distance in miles (I personally like 300 miles!)
graph_height = 300	# Distance in miles (I personally like 300 miles!)

# Number of buckets to divide lat and long deltas into
lat_buckets = 25
lon_buckets = 25


# Set to 1 if we should display the altitude indicators
show_altitude = 1

# Set to 1 if we should continuously refresh the display
continuous = 0


# Set colors to be used on the display
BLACK="\033[30m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
PINK="\033[35m"
CYAN="\033[36m"
WHITE="\033[37m"
NORMAL="\033[0;39m"

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


# Check if we should use all (historical) aircraft history data
if len(sys.argv) >= 2 and sys.argv[1] == '-a':

    # Get the list of all aircraft files in the recent history
    aircraft_files = glob.glob('/run/dump1090-fa/*i*t*.json')

    # Don't worry how "old" the reading are - use everything
    max_age = 9999.99

    # Expand the grid a bit, to show edges better
    #graph_width = (graph_width * 1.50) # Distance in miles
    #graph_height = (graph_height * 1.50)# Distance in miles
    graph_width = 500	# Distance in miles (was 450)
    graph_height = 500	# Distance in miles (was 450)

    # Don't show altitudes in the final list
    show_altitude = 0

# Check if we should keep updating the display
if len(sys.argv) >= 2 and sys.argv[1] == '-c':

    # Keep refreshing the display
    continuous = 1
    sp.call('tput clear',shell=True)




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



# Calculate graph extents
lon_min = site_lon - ((graph_width / 2) / mpd_lon)
lon_max = site_lon + ((graph_width / 2) / mpd_lon)

# Delta-per-bucket for lon
lon_bd = abs((lon_max - lon_min)/lon_buckets)
#print "lon_bd: ", lon_bd


lat_min = site_lat - ((graph_width / 2) / mpd_lat)
lat_max = site_lat + ((graph_width / 2) / mpd_lat)

# Delta-per-bucket for lat
lat_bd = (lat_max - lat_min)/lat_buckets
#print "lat_bd: ", lat_bd




#print "\nGraph left-right: ",lon_min,"-",lon_max,"longitude, ",(lon_max-lon_min)*mpd_lon," miles (",((lon_max-lon_min)*mpd_lon)/lon_buckets," miles per loc)" 
#print "      up-down   : ",lat_min,"-",lat_max,"latitude, ",(lat_max-lat_min)*mpd_lat," miles (",((lat_max-lat_min)*mpd_lat)/lat_buckets," miles per loc)"




#grid = 0
#n_dims = [2, lon_buckets+1, lat_buckets+1]
#for n in n_dims:
#    grid = [grid] * n
grid = [[[0 for k in xrange(2)] for j in xrange(lon_buckets+1)] for i in xrange(lat_buckets+1)]
#pprint(grid)
#raise SystemExit


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
    if continuous == 1:
        grid = [[[0 for k in xrange(2)] for j in xrange(lon_buckets+1)] for i in xrange(lat_buckets+1)]


    aircraft_data=open(aircraft_file)
    data = json.load(aircraft_data)
    #pprint(data)
    aircraft_data.close()

    # Figure out how many aircraft are in this file
    num_found = len(data['aircraft'])

    #print "Number of Aircraft loaded: ", num_found

    # Add aircraft from this file to total-found
    total_aircraft += num_found

    #features = ['rssi', 'seen', 'lat', 'lon', 'altitude', 'track', 'messages' ]
    #features = [ 'altitude', 'messages' ]
    for i in range(0, num_found):
        if 'rssi' in data['aircraft'][i] \
and data['aircraft'][i]['rssi'] > -49.5 \
and 'seen' in data['aircraft'][i] \
and 'lat' in data['aircraft'][i] \
and 'lon' in data['aircraft'][i] \
and data['aircraft'][i]['seen'] <= max_age:
            #print "\nAircraft[", i, "] - "
            met_criteria += 1
            #for feature in features:
	        #if feature in data['aircraft'][i]:
	            #print "    ", feature, ": ", data['aircraft'][i][feature]

	    # Calculate Signal Strength as a character, 'A' = excellent, 'Z' = bad
	    rss_idx = 0
	    rss = data['aircraft'][i]['rssi']
	    if rss <= rss_min:
	        rss_idx = 0
	    elif rss >= rss_max:
	        rss_idx = rss_buckets - 1
	    else:
	        # Compute how many "buckets" this rssi is from min
	        delta = rss_min - rss
	        rss_idx = int(delta / rss_bd) + 1
	    #print "RSS 'bucket' = ", rss_idx
	    #print "RSSI char    = ", rssi_chars[rss_buckets - rss_idx]


	    # Calculate "horizontal" (longitude) "bucket"
	    lon_idx = 0
	    lon = data['aircraft'][i]['lon']
	    if lon <= lon_min:
	        lon_idx = 0
	    elif lon >= lon_max:
	        lon_idx = lon_buckets-1
	    else:
	        # Compute how many "buckets" this lon is from min
	        delta = abs(lon_min - lon)
	        #print "lon delta = ", delta
	        lon_idx = int(delta / lon_bd)
	    #print "LON 'bucket' = ", lon_idx

	    # Calculate "vertical" (latitude) "bucket"
	    lat_idx = 0
	    lat = data['aircraft'][i]['lat']
	    if lat <= lat_min:
	        lat_idx = lat_buckets
	    elif lat >= lat_max:
	        lat_idx = 0
	    else:
	        # Compute how many "buckets" this lat is from min
	        delta = abs(lat_min - lat)
	        #print "lat delta = ", delta
	        lat_idx = lat_buckets - int(delta / lat_bd)
	    #print "LAT 'bucket' = ", lat_idx

	    # Calculate altitude character
	    alt_idx = 0
	    if 'altitude' in data['aircraft'][i]:
	        alt = data['aircraft'][i]['altitude']
	        if alt >= 40000:
		    alt_idx  = 10
	        elif alt >= 35000:
		    alt_idx  = 8
	        elif alt >= 30000:
		    alt_idx  = 7
	        elif alt >= 25000:
		    alt_idx  = 6
	        elif alt >= 20000:
		    alt_idx  = 5
	        elif alt >= 15000:
		    alt_idx  = 4
	        elif alt >= 10000:
		    alt_idx  = 3
	        elif alt >= 5000:
		    alt_idx  = 2
	        elif alt >= 3000:
		    alt_idx  = 1
	        elif alt >= 1000:
		    alt_idx  = 0
	
	    #print "ALT idx      = ", alt_idx

	    # Altitude is array[0]
	    # RSSI is array[1]

	    # See if this airplane's signal is the strongest heard (so far) from this grid position
	    if grid[lon_idx][lat_idx][1] < rss_idx:
	        #print "grid[",lon_idx,"][",lat_idx,"][1] was: ",grid[lon_idx][lat_idx][1],", is now ",rss_idx
	        grid[lon_idx][lat_idx][1] = rss_idx

	        # 2017-04-30  msipin ALWAYS pickup the altitude of the strongest signal
	        # Since this is the strongest signal for this position, also pickup the
	        # altitude that this signal was heard at.
	        #print "grid[",lon_idx,"][",lat_idx,"][0] was: ",grid[lon_idx][lat_idx][0],", is now ",alt_idx
	        grid[lon_idx][lat_idx][0] = alt_idx

	    #else:
	        #print "grid[",lon_idx,"][",lat_idx,"][1] remaining: ",grid[lon_idx][lat_idx][1]

	    # 2017-04-30  msipin  Don't pickup highest plane's altitude. We've already taken care of determining
	    #                     what altitude to pickup, above (as of change on this same date).
	    #if grid[lon_idx][lat_idx][0] < alt_idx:
	        #print "grid[",lon_idx,"][",lat_idx,"][0] was: ",grid[lon_idx][lat_idx][0],", is now ",alt_idx
	        #grid[lon_idx][lat_idx][0] = alt_idx
	    #else:
	        #print "grid[",lon_idx,"][",lat_idx,"][0] remaining: ",grid[lon_idx][lat_idx][0]

	    # (If debugging...) Display the grid that we have so far
	    #pprint(grid)


    # End, processing of this one file is complete



  # End, processing of all aircraft files are complete






  # Done looking through all aircraft for candidates

  #print "\n",time.asctime(time.gmtime()),"GMT  Aircraft:", met_criteria,"/",total_aircraft,"      "
  print '\n%s GMT     Aircraft: %d/%d      ' % (time.asctime(time.gmtime()), met_criteria,total_aircraft)



  # Altitude is array[0]
  # RSSI is array[1]
  for t in range(0, lat_buckets):
    for n in range(0, lon_buckets):
	if grid[n][t][1] > 0:

	    # Altitude
	    if show_altitude:
                if grid[n][t][0] < 2:
                    sys.stdout.write(RED)
                elif grid[n][t][0] > 7:
                    sys.stdout.write(GREEN)
                sys.stdout.write(alt_chrs[grid[n][t][0]])
                sys.stdout.write(NORMAL)
	    else:
	        sys.stdout.write(' ')

	    # RSSI
            # See if we are not showing altitude
            if show_altitude == 0:
                # Add more color gradients
	        if grid[n][t][1] < 7:
	            sys.stdout.write(RED)
	        elif grid[n][t][1] < 13:
	            sys.stdout.write(PINK)
	        elif grid[n][t][1] < 19:
	            sys.stdout.write(YELLOW)
	        elif grid[n][t][1] < 25:
	            sys.stdout.write(CYAN)
	        else:
	            sys.stdout.write(GREEN)
            else:
                # Keep colors simple
	        if grid[n][t][1] < 7:
	            sys.stdout.write(RED)
	        elif grid[n][t][1] > 24:
	            sys.stdout.write(GREEN)

	    sys.stdout.write(rssi_chars[rss_buckets - grid[n][t][1]])
	    sys.stdout.write(NORMAL)

	else:
	    # No altitude info
	    if show_altitude:
	        sys.stdout.write('.')
	    else:
	        sys.stdout.write(' ')

	    # No signal strength info
	    sys.stdout.write('.')
    print ""
  #print ""

  # Size of entire plot -
  #print "       Plot dimensions:",(lon_max-lon_min)*mpd_lon,"x",(lat_max-lat_min)*mpd_lat,"miles"

  # Size of each grid location -

  #print "Plot:",int(round((lon_max-lon_min)*mpd_lon)),"x",int(round((lat_max-lat_min)*mpd_lat)),"miles using",((lon_max-lon_min)*mpd_lon)/lon_buckets,"x",((lat_max-lat_min)*mpd_lat)/lat_buckets,"squares"

  print 'Plot: %0.fx%0.f miles using %0.1fx%0.1f mile squares' % (int(round((lon_max-lon_min)*mpd_lon)), int(round((lat_max-lat_min)*mpd_lat)),((lon_max-lon_min)*mpd_lon)/lon_buckets, ((lat_max-lat_min)*mpd_lat)/lat_buckets)




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


raise SystemExit

