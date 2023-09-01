PI=3.1415926535859

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
  
  float lon1 = hom_lon / 180 * PI  # Degrees to radians
  float lat1 = hom_lat / 180 * PI
  float lon2 = cur_lon / 180 * PI
  float lat2 = cur_lat / 180 * PI

  # Calculate azimuth
  a=atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
  hc_vector.az=a*180/PI
  if (hc_vector.az<0):
    hc_vector.az=360+hc_vector.az
 
  #  Calculate the distance from home to craft
  dLat = (lat2-lat1)
  dLon = (lon2-lon1)
  a = sin(dLat/2) * sin(dLat/2) + sin(dLon/2) * sin(dLon/2) * cos(lat1) * cos(lat2) 
  c = 2* asin(sqrt(a))  
  d = 6371000 * c    #  Radius of the Earth is 6371km
  hc_vector.dist = d

  #  Calculate elevation
  int16_t altR = cur.alt - hom.alt  #  Relative alt

  altR = altR * LimitCloseToHomeError(d, altR)
  
  hc_vector.el=atan(altR/d)
  hc_vector.el=hc_vector.el*360/(2*PI)     #  Radians to degrees
  
  return




# ********************************************************
#   Limit close-to-home elevation error due to poor vertical GPS accuracy 
def LimitCloseToHomeError(dist, alt):
  
  h_norm = 10.0     #  Normal at 10m dist
  v_norm = 5.0      #  Normal at 5m alt
  h_ratio, v_ratio, t_ratio  

  h_ratio = pow((dist / h_norm), 2)  
  v_ratio = pow((float)(alt / v_norm), 2) 
  t_ratio = h_ratio * v_ratio
  if (t_ratio > 1.0):
    t_ratio = 1
  return t_ratio  


