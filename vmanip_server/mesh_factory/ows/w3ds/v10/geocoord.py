import numpy as np
import math

coordrealEarthRadius = 6356752.3142
coordradius = 1.0
coordheightScale = coordradius / coordrealEarthRadius

def fromGeoTo3D (geo):
    dest=np.zeros((3))
    longInRad = math.radians(geo[0])
    latInRad  = math.radians(geo[1])
    cosLat = math.cos(latInRad);
        
    # Take height into account
    if (len(geo)>2):
        radius= coordradius + coordheightScale * geo[2]
    else:
        radius = coordradius

    dest[0] = radius * math.cos(longInRad) * cosLat
    dest[1] = radius * math.sin(longInRad) * cosLat
    dest[2] = radius * math.sin(latInRad)

    return dest;
    