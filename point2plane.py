#!/usr/bin/env python3
######################################################
# point2plane.py - Calculate AZ, elevation and distance (in miles) between you and an airplane at (lat,lon,altitude-in-feet)
#
# HISTORICAL INFORMATION -
#
#  2022-03-10  KA9CQL msipin  Created from the current version of satnow.py
######################################################
# You need to install this Python3 library -
#       sudo pip3 install skyfield

from skyfield.api import Topos, load, wgs84
import datetime
from datetime import timezone
#from dateutil import tz
import sys




def DegreesToRadians(tDegrees):
 return ((float(tDegrees) * math.pi) / 180.0)

def RadiansToDegrees(tRadians):
 return ((float(tRadians) * 180.0) / math.pi)

def RadiansToNaticalMiles(tRadians):
 return ((float(tRadians) * 10800.0 ) / math.pi) # 10800 = 180 * 60

def NaticalMilesToStatueMiles(tNaticalMiles):
 return (float(tNaticalMiles) * 1.15)

def StatuteMilesToNaticalMiles(tStatueMiles):
 return (float(tStatueMiles) / 1.15)

def StatuteMilesToKilometers(tStatueMiles):
 return (float(tStatueMiles) * 1.609344)


##stations_url = "https://www.amsat.org/tle/current/nasabare.txt"

##satellites = load.tle_file(stations_url)
##print('Loaded', len(satellites), 'satellites')


ts = load.timescale(builtin=True)

def gridCase(input):
    A=''
    B=''
    C=''
    D=''
    E=''
    F=''

    if (len(input)>= 4):
        chars = [char for char in input]  
        A=chars[0].upper()  # Long
        B=chars[1].upper()  # Latt
        C=chars[2]  # Long
        D=chars[3]  # Latt
        if (len(input)>= 6):
            E=chars[4].lower()  # Long
            F=chars[5].lower()  # Latt
    if ((A >= 'A') and (A <= 'R') and (B >= 'A') and (B <= 'R')):
        return(A+B+C+D+E+F)
    return('?')



def gs2LatLon(input):
    lat=0.0
    lon=0.0
    if (len(input)>= 4):
        chars = [char for char in input]  
        A=chars[0]  # Long
        B=chars[1]  # Latt
        C=chars[2]  # Long
        D=chars[3]  # Latt
        if (len(input)>= 6):
            E=chars[4]  # Long
            F=chars[5]  # Latt
            lon=getLon3(A,C,E)
            lat=getLat3(B,D,F)
        else:
            lon=getLon2(A,C)
            lat=getLat2(B,D)
    return(lat,lon)



def getLon2(LoA,LoB):
    return getLon3(LoA,LoB,'l')


def getLon3(LoA,LoB,LoC):
    a=ord(LoA) - ord('A')	# A - R (18 possibilities) 'I'/'J' = mid
    a=a*20			# 20 degrees Lon each
    b=ord(LoB) - ord('0')	# 0 - 9 (10 possibilities) '4'/'5' = mid
    b=b*2			# 2 degrees Lon each
    c=ord(LoC) - ord('a')	# a - x (24 possibilities) 'l'/'m' = mid
    #c=(c*5)/60			# 5 minutes Lon each
    c=(c/12)+(1/24)		# FROM WEBSITE - ISN'T EXPLAINED
    Lon=a+b+c-180.0
    #print("Longitude: ", Lon)
    return Lon


def getLat2(LaA,LaB):
    return getLat3(LaA,LaB,'l')


def getLat3(LaA,LaB,LaC):
    d=ord(LaA) - ord('A')
    d=d*10			# 10 degrees Lat each
    e=ord(LaB) - ord('0')
    e=e*1			# 1 degree Lat each (no adjustment needed)
    f=ord(LaC) - ord('a')
    #f=(f*2.5)/60		# 2.5 minutes Lat each
    f=(f/24)+(1/48)		# FROM WEBSITE - ISN'T EXPLAINED
    Lat=d+e+f-90.0
    #print("Latitude: ",Lat)
    return Lat

def printHeading(sat,az,el,distance):
    print("%-15s" % sat, end='')

    print('   AZ: %3d' % int(az.degrees),end='')
    #print("DEBUG: EL - ",dir(el))
    print('   EL: %3.1f' % el.degrees,end='')
    print('   Dist: {:5.2f} mi '.format(distance.km * 0.621371),end=' ')
    print('   Dist: {:5.2f} nm'.format(distance.km * 0.621371 / 1.150779),end=' ')


try:
    import configparser
except ImportError:
    print("\nERROR: Can't find 'configparser'.  Try performing 'sudo pip install ConfigParser'\n")
    sys.exit(-1)

## setup.conf contents -
## [qth]
## name1 = value1
Config = configparser.ConfigParser()
Config.read("setup.conf")

section="qth"

qth_lat = float(Config.get(section, 'lat'))
qth_lon = float(Config.get(section, 'lon'))
qth_alt = float(Config.get(section, 'alt'))


numargs = len(sys.argv)
if (numargs != 4):
    print("\nusage: %s <plane_lat> <plane_lon> <plane_altitude_in_feet>\n" % sys.argv[0])
    sys.exit(1)

# This command is argument[0]

# Start time (now) -
now = datetime.datetime.now(timezone.utc)
t0 = ts.utc(now)
##print(t0)

# Get local timezone
#tz = tz.tzlocal()


print()

# FOR NOW - Hard-code Alt1
#qth = wgs84.latlon(34.5000,-117.5000, elevation_m=0)
qth = wgs84.latlon(qth_lat,qth_lon, elevation_m=(qth_alt*0.3048))

# Plane latitude is argument[1]
p_lat=float(sys.argv[1])
# Plane longitude is argument[2]
p_lon=float(sys.argv[2])
# Plane altitude (in feet) is argument[3]
p_alt=float(sys.argv[3])


# FOR NOW - Hard-code Alt1
plane = wgs84.latlon(p_lat, p_lon, elevation_m=(int(float(p_alt)*0.3048)))

difference = plane - qth


# Find az/el
topocentric = difference.at(t0)
el, az, distance = topocentric.altaz()

printHeading("Hi!",az,el,distance)

print()
sys.exit(0)

