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
#  2017-06-02  msipin  Major refactoring. Fixed hidden bug whereby the RANGE db field was called
#                      "lon".  Still have a few TO-DOs. Some of the MAJOR ones are -
#                      TO-DO: Stop certain ICAOs from being displayed as if they were number in
#                             scientific notation
#                      TO-DO: Remove so many dang GLOBAL VARIABLES
#                      TO-DO: (there are more - search for "TO-DO:" in this code!)
#  2017-06-03  msipin  Adapted to piAware already exposing the two files we need - receiver.json
#                      and aircraft.json.
#  2017-06-09  msipin  Updated range calculation with true Great Circle distance calculation.
#  2020-10-09  msipin  Changed altitude key from "altitude" to "alt_baro" due to post-2017 PiAware change
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
KEYS_SORT_LEVEL='l'
KEYS_SORT_GSPD='g'
KEYS_SORT_VERT_RATE='v'
KEYS_SORT_RSSI='d'
KEYS_SORT_CALLSIGN='c'
KEYS_SORT_SQUAWK='s'
KEYS_SORT_TRACK='t'


# "No Such Number" - Until I can figure out how to filter out non-existent dictionary entries,
# this will be my signal that a dictionary had no value at a given key
NSN=424242424242

# JSON field names - as defined by PiAware's read-from-airplane-data-URL functionality
KEY_ICAO='hex'
KEY_CALLSIGN='flight'
KEY_LEVEL='alt_baro'
KEY_GSPD='speed'
KEY_TRACK='track'
KEY_LAT='lat'
KEY_LON='lon'
KEY_VERT_RATE='vert_rate'
KEY_SQUAWK='squawk'
KEY_RSSI='rssi'
KEY_AGE='seen'

# Global variables that will hold airplane attribute data (both for display and db writes/reads)
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

# SQLite db variables - table name, field names, field datatypes, primary key name (etc.)
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
range_field = 'range' # name of the column
range_field_type = 'FLOAT'  # column data type


# Establish ORDER BY clauses, and pick one as the default
ORDER_BY_RANGE_ASC=" {sf} ASC, {kf} DESC".format(sf=range_field, kf=key_field)
ORDER_BY_RANGE_DESC=" {sf} DESC, {kf} DESC".format(sf=range_field, kf=key_field)
ORDER_BY_ICAO_ASC=" {sf} ASC".format(sf=key_field)
ORDER_BY_ICAO_DESC=" {sf} DESC".format(sf=key_field)
ORDER_BY_LEVEL_ASC=" {sf} ASC, {kf} ASC".format(sf=level_field, kf=key_field)
ORDER_BY_LEVEL_DESC=" {sf} DESC, {kf} ASC".format(sf=level_field, kf=key_field)
ORDER_BY_GSPD_ASC=" {sf} ASC, {kf} ASC".format(sf=gspd_field, kf=key_field)
ORDER_BY_GSPD_DESC=" {sf} DESC, {kf} ASC".format(sf=gspd_field, kf=key_field)
ORDER_BY_VERT_RATE_ASC=" abs({sf}) ASC, {kf} ASC".format(sf=vert_rate_field, kf=key_field)
ORDER_BY_VERT_RATE_DESC=" abs({sf}) DESC, {kf} ASC".format(sf=vert_rate_field, kf=key_field)
ORDER_BY_RSSI_ASC=" {sf} ASC, {rf} DESC, {kf} ASC".format(sf=rssi_field, rf=range_field, kf=key_field)
ORDER_BY_RSSI_DESC=" {sf} DESC, {rf} ASC, {kf} ASC".format(sf=rssi_field, rf=range_field, kf=key_field)
ORDER_BY_CALLSIGN_ASC=" {sf} ASC, {kf} ASC".format(sf=callsign_field, kf=key_field)
ORDER_BY_CALLSIGN_DESC=" {sf} DESC, {kf} ASC".format(sf=callsign_field, kf=key_field)
ORDER_BY_SQUAWK_ASC=" {sf} ASC, {kf} ASC".format(sf=squawk_field, kf=key_field)
ORDER_BY_SQUAWK_DESC=" {sf} DESC, {kf} ASC".format(sf=squawk_field, kf=key_field)
ORDER_BY_TRACK_ASC=" {sf} ASC, {kf} ASC".format(sf=track_field, kf=key_field)
ORDER_BY_TRACK_DESC=" {sf} DESC, {kf} ASC".format(sf=track_field, kf=key_field)

# Establish the default ORDER BY clause -
ORDER_BY_CLAUSE=ORDER_BY_RANGE_DESC









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



def _create_db_tables(conn2, c2):
    global table_name1
    global key_field
    global key_field_type
    global callsign_field
    global callsign_field_type
    global level_field
    global level_field_type
    global gspd_field
    global gspd_field_type
    global track_field
    global track_field_type
    global vert_rate_field
    global vert_rate_field_type
    global squawk_field
    global squawk_field_type
    global age_field
    global age_field_type
    global rssi_field
    global rssi_field_type
    global lat_field
    global lat_field_type
    global lon_field
    global lon_field_type
    global range_field
    global range_field_type
    global NSN

    # Creating a table with 1 column and set it as PRIMARY KEY
    # note that PRIMARY KEY column must consist of unique values!
    try:
        c2.execute('CREATE TABLE {tn} ({nf} {ft} PRIMARY KEY)' \
                  .format(tn=table_name1, nf=key_field, ft=key_field_type))
        # Add CALLSIGN column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=callsign_field, ct=callsign_field_type, df=''))

        # *** vartype = INTEGER *** -
        # LEVEL=NSN
        # Add LEVEL column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=level_field, ct=level_field_type, df=NSN))
        # GSPD=NSN
        # Add GSPD column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=gspd_field, ct=gspd_field_type, df=NSN))
        # TRACK=NSN
        # Add TRACK column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=track_field, ct=track_field_type, df=NSN))
        # VERT_RATE=NSN
        # Add VERT_RATE column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=vert_rate_field, ct=vert_rate_field_type, df=NSN))
        # SQUAWK=NSN
        # Add SQUAWK column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=squawk_field, ct=squawk_field_type, df=NSN))
        # AGE=NSN
        # Add AGE column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=age_field, ct=age_field_type, df=NSN))

        # *** vartype = FLOAT *** -
        # RSSI=NSN
        # Add RSSI column with a default row value
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=rssi_field, ct=rssi_field_type, df=NSN))
        # LAT=NSN
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=lat_field, ct=lat_field_type, df=NSN))
        # LON=NSN
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=lon_field, ct=lon_field_type, df=NSN))
        # RANGE=NSN
        c2.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} DEFAULT '{df}'" \
                  .format(tn=table_name1, cn=range_field, ct=range_field_type, df=NSN))


    except sqlite3.OperationalError:
        # The most likely explanation is that the database already exists
        pass

    # Commit the database changes
    conn2.commit()


def _add_or_update_db_row(conn2, c2, icao, callsign, level, gspd, track, lat, lon, vert_rate, squawk, rssi, age):

    global NSN
    global RX_LAT
    global RX_LON
    global SLEEP_INTERVAL
    global table_name1
    global key_field
    global callsign_field
    global level_field
    global gspd_field
    global track_field
    global vert_rate_field
    global squawk_field
    global rssi_field
    global lat_field
    global lon_field
    global range_field
    global age_field

    # Calculate range in Nautical Miles (nm)
    range = _calc_range_in_nm(RX_LAT, RX_LON, lat, lon)

    # Insert (if doesn't exist already) ICAO entry in the db
    c2.execute("INSERT OR IGNORE INTO {tn} ({idf}) VALUES ('".format(tn=table_name1, idf=key_field) + icao + "')")

    # CALLSIGN
    if (callsign != ''):
        c2.execute(
            "UPDATE {tn} SET {cn}=('".format(tn=table_name1, cn=callsign_field) + callsign + "') WHERE {idf}=('".format(
                idf=key_field) + icao + "')")
    # LEVEL
    if (level == 'ground'):
        c2.execute("UPDATE {tn} SET {cn}=0".format(tn=table_name1, cn=level_field) + " WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    elif (level != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=level_field) + str(level) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    # GSPD
    if (gspd != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=gspd_field) + str(gspd) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    # TRACK
    if (track != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=track_field) + str(track) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    # VERT_RATE=NSN
    if (vert_rate != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=vert_rate_field) + str(
            vert_rate) + ") WHERE {idf}=('".format(idf=key_field) + icao + "')")
    # SQUAWK=NSN
    if (squawk != NSN):
        c2.execute(
            "UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=squawk_field) + str(squawk) + ") WHERE {idf}=('".format(
                idf=key_field) + icao + "')")
   # RSSI=NSN
    if (rssi != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=rssi_field) + str(rssi) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    # LAT=NSN
    if (lat != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=lat_field) + str(lat) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    # LON=NSN
    if (lon != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=lon_field) + str(lon) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")
    # RANGE=NSN
    if (range != NSN):
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=range_field) + str(range) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")

    conn2.commit()


    # HANDLE AGE SEPARATELY - If passed-in value is NAN, *AND* current DB entry is *ALSO* NAN, then advance the
    #                         db entry's current AGE by SLEEP_INTERVAL
    # TO-DO: Fix logic below, because it contains a bug where an existing db AGE set to NAN will be decremented by
    #        SLEEP_INTERVAL even though it's not a real "age"
    # AGE=NSN
    if (age == NSN):
        # No data, so advance this entry's age by SLEEP_INTERVAL duration
        c2.execute(
            "UPDATE {tn} SET {cn}={cn}+".format(tn=table_name1,
                                                cn=age_field) + SLEEP_INTERVAL + " WHERE {idf}='".format(
                idf=key_field) + icao + "'AND {cn} BETWEEN 0 AND ({nsn}-1))".format(cn=age_field, nsn=NSN))
    else:
        # There is data being passed in, so use it
        c2.execute("UPDATE {tn} SET {cn}=(".format(tn=table_name1, cn=age_field) + str(age) + ") WHERE {idf}=('".format(
            idf=key_field) + icao + "')")

    conn2.commit()

def _purge_old_airplane_data(conn2, c2, max_age):
    global NSN
    global table_name1
    global age_field

    c2.execute("DELETE FROM {tn} WHERE {af} > {tdo} and {af} <> {nsn}".format(tn=table_name1, af=age_field, tdo=max_age, nsn=NSN))
    conn2.commit()


def _age_all_aircraft_data_by(conn2, c2, how_much):
    global table_name1
    global NSN
    global age_field

    c2.execute("UPDATE {tn} SET {cn}={cn}+{si} WHERE {cn} BETWEEN 0 AND ({nsn}-1)".format(tn=table_name1, cn=age_field, si=how_much, nsn=NSN))
    conn2.commit()



def _calc_range_in_nm(x1, y1, x2, y2):

    distance2 = NSN
    if ((x1 != NSN) & (y1 != NSN) & (x2 != NSN) & (y2 != NSN)):
        # The following formulas assume that angles are expressed in radians.
        # So convert to radians.

        x1 = math.radians(x1)
        y1 = math.radians(y1)
        x2 = math.radians(x2)
        y2 = math.radians(y2)

        # Compute using the law of cosines.

        # Great circle distance in radians
        angle1 = math.acos(math.sin(x1) * math.sin(x2) \
                           + math.cos(x1) * math.cos(x2) * math.cos(y1 - y2))

        # Convert back to degrees.
        angle1 = math.degrees(angle1)

        # Each degree on a great circle of Earth is 60 nautical miles.
        distance1 = 60.0 * angle1


        # Compute using the Haversine formula.

        a = math.sin((x2 - x1) / 2.0) ** 2.0 \
            + (math.cos(x1) * math.cos(x2) * (math.sin((y2 - y1) / 2.0) ** 2.0))

        # Great circle distance in radians
        angle2 = 2.0 * math.asin(min(1.0, math.sqrt(a)))

        # Convert back to degrees.
        angle2 = math.degrees(angle2)

        # Each degree on a great circle of Earth is 60 nautical miles.
        distance2 = 60.0 * angle2
    return distance2




def get_key(q):
   #print 'Press a key'
   inkey = getch._Getch()
   import sys
   for i in xrange(sys.maxint):
      k=inkey()
      if k<>'':q.put(k)


if (len(sys.argv) <2):
    sys.stderr.write('\nusage: {0} <ip_address[:port]> [<ip_address2[:port]>...]\n\n'.format(sys.argv[0]))
    sys.stderr.write("Port number is optional, with a default of 8080.\n")
    sys.stderr.write("If more than one IP address is provided, all range calculations will be based\n")
    sys.stderr.write("upon the location of the receiver at the first IP address provided.\n\n")
    raise SystemExit

# Pickup IP address
NUMARGS=len(sys.argv)
ARGNO=1

# Pickup existing <stdin> environment
fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)

# Start the keystroke-handling thread
q = Queue.Queue()
t = threading.Thread(target=get_key, args = (q,))
t.daemon = True
t.start()



# Create or open the database
# TO-DO: Allow users to configure whether they want to create this database in
#        memory on on disk
#sqlite_file = '/var/tmp/pyson_db.sqlite'   # On disk - and in exactly this file
sqlite_file = ':memory:'                    # In memory
conn = sqlite3.connect(sqlite_file)
c = conn.cursor()




# Create the database tables, if they don't already exist (HINT: If using
# in-memory db, they don't, otherwise they might - depending upon whether
# or not this is the first time running this program on this host!)
_create_db_tables(conn, c)


# TO-DO: Allow users to configure whether the database should
#        be initialized (emptied) upon startup.
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


# Pickup receiver lat/lon from the FIRST (and possibly only) IP address given on the command line
# { "version" : "3.5.0", "refresh" : 1000, "history" : 120, "lat" : 34.492610, "lon" : -117.407060 }
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



should_continue=1
planes_shown=0
max_planes_to_show=(lines_to_display*2)
subprocess.call('tput clear',shell=True)




while (should_continue == 1):

  subprocess.call('tput home',shell=True)
  conn.commit()
  planes_shown=0

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
        ICAO = str(line.get(KEY_ICAO, '').encode('latin1')).upper()
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

        ############# END OF PARSING ALL URL DATA FROM THIS URL  ###############


        # Add this one aircraft's data to the database
        _add_or_update_db_row(conn, c, ICAO, CALLSIGN, LEVEL, GSPD, TRACK, LAT, LON, VERT_RATE, SQUAWK, RSSI, AGE)
  # Done, for each IP address given on the command line


  # TO-DO: Allow user to configure whether these "older" records should be purged
  # TO-DO: Allow user to specify how long this "purge duration" should be (perhaps "0" means "never delete"?)
  ## Purge all records older than "too old to use"
  _purge_old_airplane_data(conn, c, TOO_DARN_OLD)


  ## Get all data from the database using the current sort order
  c.execute("SELECT {idf} FROM {tn} WHERE {sf} < {nsn} ORDER BY {obc}".format(idf=key_field, tn=table_name1, sf=range_field, nsn=NSN, obc=ORDER_BY_CLAUSE))
  id_exists = c.fetchall()


  # Display column header
  print "  ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK | dbm        ICAO |CALLSIGN|LEVEL |GSPD|TRAK|RANGE |VRT_RT|SQWK | dbm       \r"

  for icao_data in id_exists:

    ICAO = format(icao_data[0])


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
        #print("\nNOTHING FOUND IN DB FOR ICAO = " + ICAO + "!\r")
        continue



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
        try:
	    sys.stdout.write('{:4d}'.format(TRACK))
	except:
	    sys.stdout.write('{:4.0f}'.format(TRACK))
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
  slept_for=0
  check_after=0.5
  while(q.empty() & (slept_for < SLEEP_INTERVAL)):
      time.sleep(check_after)
      slept_for=slept_for+check_after
  if (q.empty() == False):
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
          # Change order by clause to RANGE, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_RANGE_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_RANGE_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_RANGE_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_RANGE_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_RANGE_ASC
      elif (s == KEYS_SORT_LEVEL):
          # Change order by clause to LEVEL, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_LEVEL_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_LEVEL_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_LEVEL_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_LEVEL_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_LEVEL_ASC
      elif (s == KEYS_SORT_GSPD):
          # Change order by clause to GSPD, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_GSPD_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_GSPD_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_GSPD_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_GSPD_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_GSPD_ASC
      elif (s == KEYS_SORT_VERT_RATE):
          # Change order by clause to VERT_RATE-delta, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_VERT_RATE_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_VERT_RATE_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_VERT_RATE_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_VERT_RATE_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_VERT_RATE_ASC
      elif (s == KEYS_SORT_RSSI):
          # Change order by clause to RSSI, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_RSSI_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_RSSI_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_RSSI_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_RSSI_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_RSSI_DESC
      elif (s == KEYS_SORT_CALLSIGN):
          # Change order by clause to CALLSIGN, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_CALLSIGN_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_CALLSIGN_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_CALLSIGN_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_CALLSIGN_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_CALLSIGN_ASC
      elif (s == KEYS_SORT_SQUAWK):
          # Change order by clause to SQUAWK, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_SQUAWK_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_SQUAWK_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_SQUAWK_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_SQUAWK_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_SQUAWK_ASC
      elif (s == KEYS_SORT_TRACK):
          # Change order by clause to TRACK, ASC
          if (ORDER_BY_CLAUSE == ORDER_BY_TRACK_ASC):
              ORDER_BY_CLAUSE=ORDER_BY_TRACK_DESC
          elif (ORDER_BY_CLAUSE == ORDER_BY_TRACK_DESC):
              ORDER_BY_CLAUSE=ORDER_BY_TRACK_ASC
          else:
              ORDER_BY_CLAUSE=ORDER_BY_TRACK_ASC



# All aircraft's db data is now SLEEP_INTERVAL older!
_age_all_aircraft_data_by(conn, c, SLEEP_INTERVAL)



# End of while should_continue...

conn.commit()
conn.close()

# Restore <stdin>'s terminal settings
termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Move the cursor to the bottom of the screen
print("\033[{0};0H\r\n".format(lines_to_display))

raise SystemExit
