#!/usr/bin/env python3
############################################
# htest.py - An experiment to see if we can read the "aircraft.json" file and then use it to drive a pan/tilt mechanism
#            to "point at planes" as they fly overhead.
#
# HISTORICAL INFORMATION -
#
#  2022-03-15  msipin  Created from current version of "helos.py" so I could test directing a pan/tilt assembly to aim at
#                      airplanes as they pass overhead.
############################################

import sys
import json
from pprint import pprint
import glob
import time
import signal
import datetime
import subprocess
from math import atan2,sin,cos,asin,sqrt,atan
from skyfield.api import Topos, load, wgs84
import datetime
from datetime import timezone


PI=3.1415926535859

# Waveshare pan/tilt assembly's IP address -
#dst_ip1="11.11.11.11"
#dst_ip1="127.0.0.1"
# TESTING -
#dst_ip1="192.168.2.104"
# PRODUCTION -
dst_ip1="192.168.2.88"

src_prt=3131
dst_prt=3131


try:
    import configparser
except ImportError:
    print("\nERROR: Can't find 'configparser'.  Try performing 'apt-get install python-configparser'\n")
    sys.exit(-1)



def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1




# If a signal causes us to terminate, exit gracefully
def Exit_gracefully(signal, frame):
    sys.exit(0)


def printHeading(id,az,el,distance):

    print('ID: %s' % id,end='')
    print('   AZ: %3d' % int(az.degrees),end='')
    #print("DEBUG: EL - ",dir(el))
    print('   EL: %3.1f' % el.degrees,end='')
    print('   Dist: {:5.2f} mi '.format(distance.km * 0.621371),end=' ')
    print('   Dist: {:5.2f} nm'.format(distance.km * 0.621371 / 1.150779))



def GetAzEl(hom_lat, hom_lon, hom_alt, cur_lat, cur_lon, cur_alt):
  ##
  ## 
  ##  Aviation Formulary V1.33, by Ed Williams
  ##  http://williams.best.vwh.net/avform.htm   
  ##
  ##  The algorithm it gives for hc_vector.az bearing between two points is 
  ##  this:
  ##
  ##   tc1=mod(atan2(sin(lon2-lon1)*cos(lat2),
  ##          cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1)),
  ##          2*pi)
  ##
  
  print(" hom_lat = %3.7f" % hom_lat)
  print(" hom_lon = %3.7f" % hom_lon)
  print(" hom_alt = %6f" % hom_alt)
  print(" cur_lat = %3.7f" % cur_lat)
  print(" cur_lon = %3.7f" % cur_lon)
  print(" cur_alt = %6f" % cur_alt)
  
  lon1 = hom_lon / 180 * PI  # Degrees to radians
  lat1 = hom_lat / 180 * PI
  lon2 = cur_lon / 180 * PI
  lat2 = cur_lat / 180 * PI

  # Calculate azimuth
  a=atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
  hc_vector_az=a*180/PI
  if (hc_vector_az<0):
    hc_vector_az=360+hc_vector_az
  print("Az: ",hc_vector_az)
 
  #  Calculate the distance from home to craft
  dLat = (lat2-lat1)
  dLon = (lon2-lon1)
  a = sin(dLat/2) * sin(dLat/2) + sin(dLon/2) * sin(dLon/2) * cos(lat1) * cos(lat2) 
  c = 2* asin(sqrt(a))  
  d = 6371000 * c    #  Radius of the Earth is 6371km
  hc_vector_dist = d

  #  Calculate elevation
  altR = cur_alt - hom_alt  #  Relative alt

  altR = altR * LimitCloseToHomeError(d, altR)
  
  hc_vector_el=atan(altR/d)
  hc_vector_el=hc_vector_el*360/(2*PI)     #  Radians to degrees
  print("El: ",hc_vector_el)

  
  return hc_vector_az, hc_vector_el




# ********************************************************
#   Limit close-to-home elevation error due to poor vertical GPS accuracy 
def LimitCloseToHomeError(dist, alt):
  
  h_norm = 10.0     #  Normal at 10m dist
  v_norm = 5.0      #  Normal at 5m alt

  h_ratio = pow((dist / h_norm), 2)  
  v_ratio = pow((float)(alt / v_norm), 2) 
  t_ratio = h_ratio * v_ratio
  if (t_ratio > 1.0):
    t_ratio = 1
  return t_ratio  







if __name__ == "__main__":


  # Read alert.config
  Config = configparser.ConfigParser()
  Config.read("alerts.conf")
  #print(Config.sections())

  acct=ConfigSectionMap("default")['user']


  email_list = []


  # Pickup whom to email alerts to from the config file
  try:
      send_tos=ConfigSectionMap(acct)['email_list']
      print("\nalerts.conf: email_list = [{0}]".format(send_tos))
      email_list = send_tos.split()
  except KeyError:
      print("\nERROR: No value for [{0}][email_list] in config file\n".format(acct))


  # If provided on the command line, add to alert list
  #print "Arguments count: ", len(sys.argv)
  for i, arg in enumerate(sys.argv):
      #print "Argument ",i," : ",arg
      if i >= 1:
          email_list.append(arg)


  print("EMAIL LIST: ",email_list)

  ## If debugging, prolly wanna exit now...
  #sys.exit(-1)

  
  '''
    Categories taken from /home/dump1090/public_html/markers.js, excpet UAVs, which
    was found somewhere else and added here by hand -

    "A1" : 'cessna',
    "A2" : 'jet_nonswept',
    "A3" : 'airliner',
    "A4" : 'heavy_2e',
    "A5" : 'heavy_4e',           # "Wake-inducing" aircraft, including air-to-air refueling tankers --but-- also, "large" Airliners =(
    "A6" : 'hi_perf',            # Appears to include Lear Jets, Bombardier
    "A7" : 'helicopter',
    "B1" : 'cessna',
    "B2" : 'balloon',
    "B4" : 'cessna',
    "B6" : 'UAV',    # NOT FOUND IN SOURCE (added by hand) - THIS ONE HAS UAVs!!!!
    "B7" : 'hi_perf',
    'C0' : 'ground_unknown',
    'C1' : 'ground_emergency',
    'C2' : 'ground_service',
    'C3' : 'ground_fixed',
    "C4" : 'ground_fixed',
    "C5" : 'ground_fixed',
    "C6" : 'ground_unknown',
    "C7" : 'ground_unknown'
  '''

  # Develop alert categories
  alert_categories = []

  try:
      categories=ConfigSectionMap(acct)['categories']
      print("\nalerts.conf: categories = [{0}]".format(categories))
      alert_categories = categories.split()
  except KeyError:
      print("\nERROR: No value for [{0}][categories] in config file\n".format(acct))
  

  print("CATEGORIES: ",alert_categories)

  ## If debugging, prolly wanna exit now...
  #sys.exit(-1)



  ## If debugging, prolly wanna exit now...
  ##sys.exit(-1)


  ## If debugging, prolly wanna exit now...
  #sys.exit(-1)



  ## If debugging, prolly wanna exit now...
  ##sys.exit(-1)


  
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
  #MAX_AGE = (30.0*60.0)	# 30 mins - use for Production
  MAX_AGE = (30.0)	# 30 seconds
  #MAX_AGE = (24.0*60.0*60.0)	# Use for testing

  # Alert window - Max. age for an alert to be generated
  # NOTE: MUST be more than recheck_interval
  alert_window = (90)  # 90 seconds - use for Production
  #alert_window = MAX_AGE # Use for testing
  
  # Re-check interval (in seconds) -  how long to sleep between checks for new aircraft
  # NOTE: MUST be less than alert_window
  ##recheck_interval = (1*60) # 1 minute
  recheck_interval = (1) # in seconds
  
  # Date that file was created
  file_date = 0;
  
  # Set to 1 if we should continuously refresh the display
  continuous = 1
  
  
  signal.signal(signal.SIGINT, Exit_gracefully)
  
  
  signal.signal(signal.SIGINT, Exit_gracefully)
  
  
  
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
      print("Site Latitude: ", site_lat)
      site_lon = site['lon']
      print("Site Longitude: ", site_lon)
      #site_alt = site['alt']
      site_alt = 6.0 # NOT IN CONFIG FILE!
      print("Site Altitude: ", site_alt)
  else:
      print("\nERROR: Site's position is unknown.  Can not continue.\n")
      raise SystemExit
  
  qth = wgs84.latlon(site_lat,site_lon, elevation_m=(site_alt*0.3048))
  ts = load.timescale(builtin=True)
  
  
  
  met_criteria=0
  total_reports=0

  while met_criteria == 0:
  
    ahora = time.time()
    #print "\nTIME_NOW: ", ahora
    #print "TIME_NOW: ",datetime.datetime.utcfromtimestamp(ahora)
  
    max_age = ahora - MAX_AGE 
    #print "\nMAX_AGE:  ", max_age
    #print "MAX_AGE:  ", datetime.datetime.utcfromtimestamp(max_age)
  
    # Dictionary of all helicopter data
    helo_dict = {}
  
    # The most recent aircraft signal-report file -
    #aircraft_files = [ '/run/dump1090-fa/aircraft.json' ]
    aircraft_files = glob.glob('/run/dump1090-fa/history*.json')
    aircraft_files.append('/run/dump1090-fa/aircraft.json')
  
    closest_hex="?"
    closest_metric=180.0**2+90.0**2
    closest_lat=site_lat*10
    closest_lon=site_lon*10
    closest_alt=900000.0
    for aircraft_file in aircraft_files:

      try:
      	aircraft_data=open(aircraft_file)
      except IOError:
      	print("\nError opening file [{0}]\n".format(aircraft_file))
      	continue


      data = json.load(aircraft_data)
      #pprint(data)
      aircraft_data.close()
  
      # Pickup file-creation date
      file_date = data['now']
      #print "\nFile-creation date: ", file_date
  
  
      # Figure out how many aircraft are in this file
      num_found = len(data['aircraft'])
  
      #print "\nNumber of Aircraft found: ", num_found
  
      # Add reports from this file to total-found
      total_reports += num_found



      for i in range(0, num_found):
          if 'rssi' in data['aircraft'][i] \
and data['aircraft'][i]['rssi'] > -49.5 \
and 'seen' in data['aircraft'][i]:
  
              seen = file_date - data['aircraft'][i]['seen']
              #print "\nseen : ", seen,
              #age = ahora - seen
              age = seen
              #print "\nage of siting: ", age,
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
                      'flight': 'unk',
                      'category': 'unk',
                      'oldest_age': 9999999999,
                      'newest_pos': pos,
                      'newest_age': -9999999999
                  }
  
                  # If hex is NOT in helo_dict
                  if hex not in helo_dict.keys(): 
                      #print "\n\nHex: ",hex, " Not present - adding it now...",
                      # Add default info to helo_dict
                      helo_dict[hex] = aircraft
                  #else: 
                  #    print "\n\nHex: ",hex, " already present",
  
                  #print "\n", age,
                  met_criteria += 1
  
                  #print "\nFound age of: ", datetime.datetime.utcfromtimestamp(age)
                  #try:
                  #    print "  was newest: ", datetime.datetime.utcfromtimestamp(helo_dict[hex]['newest_age'])
                  #except:
                  #    print "unk"
  
                  #try:
                  #    print " was pos age: ", datetime.datetime.utcfromtimestamp(helo_dict[hex]['newest_pos']['age'])
                  #except:
                  #    print "unk"
  
                  #try:
                  #   print "  was oldest: ", datetime.datetime.utcfromtimestamp(helo_dict[hex]['oldest_age'])
                  #except:
                  #    print "unk"

                  flight = helo_dict[hex]['flight']
                  #print "DEBUG: flight was   : ",flight
                  try:
                     if data['aircraft'][i]['flight'] != "unk":
                        #print "DEBUG: found flight attribute!"
                        flight = data['aircraft'][i]['flight']
                        #print "DEBUG: flight now is: ",flight
                        helo_dict[hex].update({'flight': flight})
                  except:
                     # Do nothing...
                     nop=1;
                     #print "      no flight number"
                  #print "      flight: ", flight

                  category = helo_dict[hex]['category']
                  #print "DEBUG: category was   : ",category
                  try:
                     if data['aircraft'][i]['category'] != "unk":
                        #print "DEBUG: found category attribute!"
                        category = data['aircraft'][i]['category']
                        #print "DEBUG: category now is: ",category
                        helo_dict[hex].update({'category': category})
                  except:
                     # Do nothing...
                     #print "      no category"
                     nop=1;
                  #print "    category: ", category

  
                  # Keep oldest age for hex
                  if age < helo_dict[hex]['oldest_age']:
                      #print "\nFound older age of: ",age
                      #print "Found older age of: ", datetime.datetime.utcfromtimestamp(age)
                      helo_dict[hex].update({'oldest_age': age})
  
  
                  # Keep newest lat/long/alt for hex
                  if 'lat' in data['aircraft'][i] \
and 'lon' in data['aircraft'][i] \
and 'alt_baro' in data['aircraft'][i] \
and age > helo_dict[hex]['newest_pos']['age']:
  
                      #print "\nFound newer position with age of: ",age
                      #print "Found newer position with age of: ", datetime.datetime.utcfromtimestamp(age)
                      helo_dict[hex]['newest_pos'].update({
                          'age': age,
                          'lat': data['aircraft'][i]['lat'],
                          'lon': data['aircraft'][i]['lon'],
                          'alt': data['aircraft'][i]['alt_baro']
                      })
  
                      # See if plane is "up in the air"... LOL
                      if (data['aircraft'][i]['alt_baro'] != "ground") and (data['aircraft'][i]['alt_baro'] >= 500):
                          # Compute "rough guess" of distance-to-plane
                          plane_lat = data['aircraft'][i]['lat']
                          plane_lon = data['aircraft'][i]['lon']
                          plane_alt = data['aircraft'][i]['alt_baro']
                          curr_metric = abs(site_lat-plane_lat)**2+abs(site_lon-plane_lon)**2
                          if (curr_metric < closest_metric):
                              closest_hex=hex
                              closest_metric = curr_metric
                              closest_lat = plane_lat
                              closest_lon = plane_lon
                              closest_alt = plane_alt
  
  
                  # keep newest age for hex
                  if age > helo_dict[hex]['newest_age']:
                      #print "\nFound newer age of: ",age
                      #print "Found newer age of: ", datetime.datetime.utcfromtimestamp(age)
                      helo_dict[hex].update({'newest_age': age})
  
              # End, sighting is recent enough to be considered
  
      # End, processing of this one file is complete
  
    # End, processing of all aircraft files are complete

  
    # Done looking through all aircraft for candidates

    print("*******************************************************")
    # Display where currently-closest plane is (lat/lon)
    print("Closest plane [%s] is currently at lat/lon/alt [%.4f %.4f %s]" % (closest_hex,closest_lat,closest_lon,closest_alt))



    # NOT SUPER ACCURATE AT HEIGHT AND +/- 15 DEGREES -
    # AZ,EL = GetAzEl(site_lat, site_lon, site_alt, closest_lat, closest_lon, closest_alt)

    # Start time (now) -
    now = datetime.datetime.now(timezone.utc)
    t0 = ts.utc(now)
    ##print(t0)

    plane = wgs84.latlon(closest_lat, closest_lon, elevation_m=(int(float(closest_alt)*0.3048)))
    difference = plane - qth

    # Find az/el
    topocentric = difference.at(t0)
    el, az, distance = topocentric.altaz()
    AZ = int(az.degrees)
    EL = int(el.degrees)
    printHeading(closest_hex,az,el,distance)


    proc = subprocess.Popen(['azelSend',str(int(AZ)),str(int(EL))],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    data1 = proc.stdout.read().decode().rstrip('\r').rstrip('\n').replace('\n',',')
    print("\nazelSend.py returned: %s" % data1)

    print('%s GMT     Sightings %d/%d Records' % (time.asctime(time.gmtime()), met_criteria,total_reports))
  
  
    if continuous == 1:
      met_criteria=0
      total_reports=0
      sys.stdout.flush()
      time.sleep(recheck_interval)
  
    else:
      quit()
  
  
  raise SystemExit


