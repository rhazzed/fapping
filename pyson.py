#! /usr/bin/python
############################################
# pyson.py - A Python script to extract real-time ADS-B aircraft beacon data from a PiAware
#
# HISTORICAL INFORMATION -
#
#  2017-05-31  msipin  Created.
#  2017-06-01  msipin  Built database from received data. Used that to produce display, rather
#                      than using only the last-received message's data. Added keystroke-capture
#                      in a separate thread (NOTE: Requires termios - can Winblows do that?)
############################################

import sys, math, time
import urllib, json
import subprocess
import sqlite3
import getch
import Queue
import threading
import time
import sys
import sys, tty, termios

KEYS_QUIT='q'
KEYS_SORT_ICAO='i'
KEYS_SORT_RANGE='r'


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
KEY_AGE='seen'

# Global variables
ICAO=''
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

SLEEP_INTERVAL=4

def init_display_vars():
    global ICAO
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

    ICAO=''
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

def get_key(q):
   #print 'Press a key'
   inkey = getch._Getch()
   import sys
   for i in xrange(sys.maxint):
      k=inkey()
      if k<>'':q.put(k)


# (Approx.) Miles-per-degree of latitude/longitude - accuracy is
# not as important; only being used for rough estimation
# of RANGE
mpd_lat = 69.0535	# Avg, equator-to-pole
mpd_lon = 53.0000	# At 40 degrees N/S




if (len(sys.argv) <2):
    sys.stdout.write('\nUsage: ')
    sys.stdout.write(sys.argv[0])
    sys.stdout.write(' <ip_address>\n\n')
    raise SystemExit

# Pickup IP address
IP_ADDR=sys.argv[1]

# Pickup existing <stdin> environment
fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)

# Start the keystroke-handling thread
q = Queue.Queue()
t = threading.Thread(target=get_key, args = (q,))
t.daemon = True
t.start()



# Create or open the database
sqlite_file = '/var/tmp/pyson_db.sqlite'
conn = sqlite3.connect(sqlite_file)
c = conn.cursor()

table_name1 = 'airplanes'
key_field = KEY_ICAO # name of the column
key_field_type = 'STRING'  # column data type
callsign_field = KEY_CALLSIGN # name of the column
callsign_field_type = 'STRING'  # column data type
level_field = KEY_LEVEL # name of the column
level_field_type = 'INTEGER'  # column data type
gspd_field = KEY_GSPD # name of the column
gspd_field_type = 'INTEGER'  # column data type
track_field = KEY_TRACK # name of the column
track_field_type = 'INTEGER'  # column data type
vert_rate_field = KEY_VERT_RATE # name of the column
vert_rate_field_type = 'INTEGER'  # column data type
squawk_field = KEY_SQUAWK # name of the column
squawk_field_type = 'INTEGER'  # column data type
age_field = KEY_AGE # name of the column
age_field_type = 'INTEGER'  # column data type
rssi_field = KEY_RSSI # name of the column
rssi_field_type = 'FLOAT'  # column data type
lat_field = KEY_LAT # name of the column
lat_field_type = 'FLOAT'  # column data type
lon_field = KEY_LON # name of the column
lon_field_type = 'FLOAT'  # column data type
range_field = KEY_LON # name of the column
range_field_type = 'FLOAT'  # column data type


# Creating a second table with 1 column and set it as PRIMARY KEY
# note that PRIMARY KEY column must consist of unique values!
try:
    c.execute('CREATE TABLE {tn} ({nf} {ft} PRIMARY KEY)'\
        .format(tn=table_name1, nf=key_field, ft=key_field_type))
    # Add CALLSIGN column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=callsign_field, ct=callsign_field_type, df=''))

# *** vartype = INTEGER *** -
# LEVEL=NSN
    # Add LEVEL column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=level_field, ct=level_field_type, df=NSN))
# GSPD=NSN
    # Add GSPD column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=gspd_field, ct=gspd_field_type, df=NSN))
# TRACK=NSN
    # Add TRACK column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=track_field, ct=track_field_type, df=NSN))
# VERT_RATE=NSN
    # Add VERT_RATE column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=vert_rate_field, ct=vert_rate_field_type, df=NSN))
# SQUAWK=NSN
    # Add SQUAWK column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=squawk_field, ct=squawk_field_type, df=NSN))
# AGE=NSN
    # Add AGE column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=age_field, ct=age_field_type, df=NSN))

# *** vartype = FLOAT *** -
# RSSI=NSN
    # Add RSSI column with a default row value
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=rssi_field, ct=rssi_field_type, df=NSN))
# LAT=NSN
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=lat_field, ct=lat_field_type, df=NSN))
# LON=NSN
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=lon_field, ct=lon_field_type, df=NSN))
# RANGE=NSN
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'"\
        .format(tn=table_name1, cn=range_field, ct=range_field_type, df=NSN))


except sqlite3.OperationalError:
    pass

# Commit the database changes
conn.commit()



############ CAUTION! #############
############ CAUTION! #############
############ CAUTION! #############
############ CAUTION! #############
## DELETE ALL DATABASE RECORDS, as we're just launching the tool....?
#c.execute("DELETE FROM {tn}".format(tn=table_name1))
#conn.commit()
############ CAUTION! #############
############ CAUTION! #############
############ CAUTION! #############
############ CAUTION! #############



# TO FIND OUT THE NUMBER OF LINES AVAILABLE ON THE SCREEN -
cmd='echo "lines"|tput -S'
result = subprocess.check_output(cmd, shell=True)
lines_to_display=int(result)-1
#`echo "cols"|tput -S`
##print "Number of screen lines = %d" % lines_to_display
##print "Screen height = %s" % height




# Pickup receiver lat/lon
# { "version" : "3.5.0", "refresh" : 1000, "history" : 120, "lat" : 34.492610, "lon" : -117.407060 }
url = "http://" + IP_ADDR + ":8080/receiver.json"
response = urllib.urlopen(url)
line = json.loads(response.read())
RX_LAT = line.get(KEY_LAT, NSN)
#print '\tRX_LAT = %s' % RX_LAT
RX_LON = line.get(KEY_LON, NSN)
#print '\tRX_LON = %s' % RX_LON

if ((RX_LAT == NSN) | (RX_LON == NSN)):
    print '\nERROR: Receiver location unknown.\nExiting!'
    raise SystemExit


# Establish ORDER BY clauses, and pick one as the default
ORDER_BY_RANGE_ASC=" {sf} ASC, {rssi} DESC".format(sf=range_field, rssi=rssi_field)
ORDER_BY_RANGE_DESC=" {sf} DESC, {rssi} DESC".format(sf=range_field, rssi=rssi_field)
ORDER_BY_ICAO_ASC=" {sf} ASC".format(sf=key_field)
ORDER_BY_ICAO_DESC=" {sf} DESC".format(sf=key_field)
ORDER_BY_CLAUSE=ORDER_BY_RANGE_DESC



should_continue=1
planes_shown=0
max_planes_to_show=(lines_to_display*2)
subprocess.call('tput clear',shell=True)
while (should_continue == 1):

  subprocess.call('tput home',shell=True)
  conn.commit()
  planes_shown=0

  print "  ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK |RSSI        ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK |RSSI       \r"

  url = "http://" + IP_ADDR + ":8080/aircraft.json"
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
    AGE = line.get(KEY_AGE, NSN)
    #print '\tAGE = %s' % AGE

    # CONVERT LAT+LONG into RANGE (nm)
    RANGE=NSN
    if ((LAT != NSN) & (LON != NSN)):
        DLAT=RX_LAT-LAT
        # Calculate approximate distance (in miles) of delta in latitude
        LAT_DELTA_MILES=DLAT*mpd_lat

        DLON=RX_LON-LON
        # Calculate approximate distance (in miles) of delta in longitude
        LON_DELTA_MILES=DLON*mpd_lon

        # Calculate the approximate range (in nautical miles)
        RANGE=math.sqrt((LAT_DELTA_MILES*LAT_DELTA_MILES)+(LON_DELTA_MILES*LON_DELTA_MILES))*0.868976


    # Insert (if doesn't exist already) ICAO entry in the db
    c.execute("INSERT OR IGNORE INTO {tn} ({idf}) VALUES ('".format(tn=table_name1, idf=key_field) + ICAO + "')")

    # CALLSIGN
    if (CALLSIGN != ''):
        c.execute("UPDATE {tn} SET {cn}=('".format(tn=table_name1, cn=callsign_field) + CALLSIGN + "') WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # LEVEL 
    if (LEVEL == 'ground'):
        c.execute("UPDATE {tn} SET {cn}=0".format(tn=table_name1, cn=level_field) + " WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    elif (LEVEL != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=level_field) + str(LEVEL) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # GSPD
    if (GSPD != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=gspd_field) + str(GSPD) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # TRACK
    if (TRACK != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=track_field) + str(TRACK) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # VERT_RATE=NSN
    if (VERT_RATE != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=vert_rate_field) + str(VERT_RATE) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # SQUAWK=NSN
    if (SQUAWK != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=squawk_field) + str(SQUAWK) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # AGE=NSN
    if (AGE == NSN):
        # No data, so advance this entry's age by SLEEP_INTERVAL duration
        c.execute("UPDATE {tn} SET {cn}={cn}+".format(tn=table_name1, cn=age_field) + SLEEP_INTERVAL + " WHERE {idf}='".format(idf=key_field) + ICAO + "')")
    else:
        # There is data, so use it
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=age_field) + str(AGE) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # RSSI=NSN
    if (RSSI != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=rssi_field) + str(RSSI) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # LAT=NSN
    if (LAT != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=lat_field) + str(LAT) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # LON=NSN
    if (LON != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=lon_field) + str(LON) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
    # RANGE=NSN
    if (RANGE != NSN):
        c.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=range_field) + str(RANGE) + ") WHERE {idf}=('".format(idf=key_field) + ICAO + "')")
  ############# END OF PARSING ALL URL DATA  ###############
  conn.commit()


  ## Purge all records older than "too old to use"
  c.execute("DELETE FROM {tn} WHERE {af} > {tdo} and {af} <> {nsn}".format(tn=table_name1, af=age_field, tdo=TOO_DARN_OLD, nsn=NSN))
  #id_exists = c.fetchall()
  conn.commit()

  ## Get all data from the database in max-range order, desc
  #retrieve-all-ICAOs-ordered by max-range descending
  c.execute("SELECT {idf} FROM {tn} WHERE {sf} < {nsn} ORDER BY {obc}".format(idf=key_field, tn=table_name1, sf=range_field, nsn=NSN, obc=ORDER_BY_CLAUSE))
  id_exists = c.fetchall()
  for icao_data in id_exists:

    ICAO=format(icao_data[0])


################################
################################

    ############# START OF DATABSE INTERACTION ###############
    # Fetch ALL data from the database
    #ICAO = str(line.get(KEY_ICAO, '')).upper()
    #CALLSIGN = str(line.get(KEY_CALLSIGN, '')).upper()
    #LEVEL = line.get(KEY_LEVEL, NSN)
    #GSPD = line.get(KEY_GSPD, NSN)
    #TRACK = line.get(KEY_TRACK, NSN)
    #LAT = line.get(KEY_LAT, NSN)
    #LON = line.get(KEY_LON, NSN)
    #VERT_RATE = line.get(KEY_VERT_RATE, NSN)
    #SQUAWK= line.get(KEY_SQUAWK, NSN)
    #RSSI = line.get(KEY_RSSI, NSN)
    #AGE = line.get(KEY_AGE, NSN)
    #RANGE=KEY_RANGE
    c.execute("SELECT {cn1},{cn2},{cn3},{cn4},{cn5},{cn6},{cn7},{cn8},{cn9},{cn10},{cn11} FROM {tn} WHERE {idf}=('".format( \
           cn1=callsign_field, \
           cn2=level_field, \
           cn3=gspd_field, \
           cn4=track_field, \
           cn5=lat_field, \
           cn6=lon_field, \
           cn7=vert_rate_field, \
           cn8=squawk_field, \
           cn9=rssi_field, \
           cn10=age_field, \
           cn11=range_field, \
           tn=table_name1, idf=key_field) + ICAO + "')")
    id_exists = c.fetchone()
    if id_exists:
        CALLSIGN=format(id_exists[0])
        LEVEL=id_exists[1]
        GSPD=id_exists[2]
        TRACK=id_exists[3]
        LAT=id_exists[4]
        LON=id_exists[5]
        VERT_RATE=id_exists[6]
        SQUAWK=id_exists[7]
        RSSI=id_exists[8]
        AGE=id_exists[9]
        RANGE=id_exists[10]
    else:
        print("\nNOTHING FOUND IN DB FOR ICAO = " + ICAO + "!\r")



    # If AGE too old, continue
    # Don't want to display information that is "too old"
    if (AGE > max_age):
        continue


    # If there is more to display than we have room to display, stop displaying more
    if (planes_shown >= max_planes_to_show):
        break


    if ((planes_shown > 0) & (planes_shown < max_planes_to_show)):
        if ((planes_shown % 2) == 0):
            sys.stdout.write('\r\n')
        else:
            sys.stdout.write('    ')


    # Display this ICAO's data

    #print "%7s|%8s|%6s|%4s|%4s|%11s|%11s|%6s|%5s|%6s" % '{:7s}'.format(ICAO), '{:8s}'.format(CALLSIGN), '{:6s}'.format(LEVEL), '{:4s}'.format(GSPD), '{:4s}'.format(TRACK), '{:11s}'.format(LAT), '{:6s}'.format(LON), '{:5s}'.format(VERT_RATE), '{:6s}'.format(SQUAWK), '{:xs}'.format(RSSI)
    sys.stdout.write('{:7s}'.format(ICAO))
    sys.stdout.write('|')
    sys.stdout.write('{:8s}'.format(CALLSIGN))
    sys.stdout.write('|')
    if (LEVEL != NSN):
        if ((LEVEL == 'ground') | (LEVEL == '0')):
            sys.stdout.write('{:6s}'.format('ground'))
        else:
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
    if (RANGE != NSN):
        sys.stdout.write('{:-6.1f}'.format(RANGE))
    else:
        sys.stdout.write('{:6s}'.format(''))
    sys.stdout.write('|')
    if (VERT_RATE != NSN):
        sys.stdout.write('{:6d}'.format(VERT_RATE))
    else:
        sys.stdout.write('{:6s}'.format(''))
    sys.stdout.write('|')
    if (SQUAWK != NSN):
        sys.stdout.write('{:5d}'.format(SQUAWK))
    else:
        sys.stdout.write('{:5s}'.format(''))
    sys.stdout.write('|')
    if (RSSI != NSN):
        sys.stdout.write('{:6s}'.format(str(('{:-2.1f}'.format(RSSI)))))
    else:
        sys.stdout.write('{:6s}'.format(''))

    planes_shown=planes_shown+1

    #instr = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9}".format(ICAO, CALLSIGN, LEVEL, GSPD, TRACK, LAT, LON, VERT_RATE, SQUAWK, RSSI)
    #print instr




    ############# END OF DATABSE INTERACTION ###############
    ################################
    ################################
    # DONE Displaying this ICAO's data
  # DONE for each ICAO retrieved from the database


  # Clear the screen to the EOL/bottom
  # If there were fewer planes than allowed, clear the remaining screen real estate
  while (planes_shown < max_planes_to_show):
      # Newline -or- space
      if ((planes_shown % 2) == 0):
          sys.stdout.write('\r\n')
      else:
          sys.stdout.write('    ')

      # Show a "blank plane"
      sys.stdout.write('                                                             ')

      planes_shown=planes_shown+1





  sys.stdout.flush()
  subprocess.call('tput home',shell=True)

  # See if there are any keystrokes to read
  if q.empty():
      time.sleep(SLEEP_INTERVAL)
  else:
      s = q.get()
      #print "Found {} in the queue!".format(s)
      if (s == KEYS_QUIT):
          should_continue=0
      elif (s == KEYS_SORT_ICAO):
          # Change order by clause to ICAO, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_ICAO_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_ICAO_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_ICAO_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_ICAO_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_ICAO_ASC
      elif (s == KEYS_SORT_RANGE):
          # Change order by clause to RANGE, DESC
          if (ORDER_BY_CLAUSE == ORDER_BY_RANGE_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_RANGE_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_RANGE_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_RANGE_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_RANGE_DESC


  # All db entries are now SLEEP_INTERVAL older!
  c.execute("UPDATE {tn} SET {cn}={cn}+{si}".format(tn=table_name1, cn=age_field, si=SLEEP_INTERVAL))
  conn.commit()

# End of while should_continue...

conn.commit()
conn.close()

# Restore <stdin>'s terminal settings
termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Move the cursor to the bottom of the screen
lines_to_display=int(result)-1
print("\033[{0};0H\r\n".format(lines_to_display))

raise SystemExit


#########################
# Potentially useful URLs  -
# 
# http://${IP_ADDR}:8080/receiver.json
# { "version" : "3.5.0", "refresh" : 1000, "history" : 120, "lat" : 34.492610, "lon" : -117.407060 }
# 
# 
# http://${IP_ADDR}:8080/aircraft.json
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
