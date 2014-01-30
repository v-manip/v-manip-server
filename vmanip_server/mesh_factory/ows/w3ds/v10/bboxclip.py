from collections import namedtuple
from math import hypot
from collections import OrderedDict

#===============================================================================
# minimal 2D vector arithmetic with one additional parameter (e.g.texture coordinate)
#
class v2dp(namedtuple('v2dp', ('x', 'y', 'u'))):
    __slots__ = ()

    def __add__(self, other):
        return type(self)(self.x + other.x, self.y + other.y, self.u + other.u)

    def __sub__(self, other):
        return type(self)(self.x - other.x, self.y - other.y, self.u - other.u)

    def __mul__(self, other):
        return type(self)(self.x * other, self.y * other, self.u * other)

    def __div__(self, other):
        return type(self)(self.x / other, self.y / other, self.u / other)

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def distance_to(self, other):
        return hypot((self.x - other.x), (self.y - other.y))
    
    def abs(self):
        return self.distance_to(type(self)(0.0, 0.0, 0.0))
    
    def __repr__(self):
        return "[%5.2f, %5.2f] (%5.2f)"%(self.x, self.y, self.u)
        
#===============================================================================
#
# A line represented by a normalized normal vector and the
# distance to the origin. 
# Equation for points p on the line: Normal dot p == Distance
# "with_boundary" defines if points on the line are to be considered
# on the positive side ("inside")
#
class InfiniteLine2d:
    def __init__(self, x1, y1, x2, y2, with_boundary=True):
        self.Normal=v2dp(y2-y1, x1-x2, 0)
        self.Normal=self.Normal/self.Normal.abs()
        self.with_boundary=with_boundary
        self.offset=0
        self.offset=self.distance(v2dp(x1, y1, 0))
        
    def distance(self, point):
        return self.Normal.dot(point)-self.offset

#===============================================================================


#===============================================================================
# 
# Clip the polyline at the supplied line. 
# it returns a list of polylines containing all "inside" points
#    (points on the positive side of the line) 
# eps is a tolerance for numerical stability:
#  points with an absolute distance<eps are considered on the line
#  to make glancing intersections numerically stable
#
def ClipPolylineHalfspace(polyline, line, eps=1e-8):

    # constants for point classification
    inside=1
    outside=2
    border=3
    
    pa=[]   # intermediate polyline
    # first pass: add intersection points and classify all points
    for vi in range (0, len(polyline)):
        p1=polyline[vi]
        h1=line.distance(p1)
        h1p = h1 > eps
        h1n = h1 < -eps
        if (vi>0) and ((h0p and h1n) or (h0n and h1p)): # points are on opposite sides: 
            pn = (p0 + (p1 - p0) * (h0 / (h0 - h1))) # clip segment
            pa.append((pn, border))  # insert new point in intermediate poly
            
        # mark points appropriately     
        if h1p:
            pa.append((p1, inside))
        elif h1n:
            pa.append((p1, outside))
        else:
            pa.append((p1, border))
        h0p=h1p
        h0n=h1n
        p0=p1
        h0=h1

    #===========================================================================
    # for (p, m) in pa:
    #     print p,
    #     if m==inside:
    #         print " inside"
    #     elif m==outside:
    #         print " outside"
    #     elif m==border:
    #         print " border"
    #     else:
    #         print"  ERROR!"        
    # print
    #===========================================================================
        
    edges=list()
    edge=OrderedDict()
    p0=pa[0][0]
    h0=pa[0][1]
    
    # 2nd pass: classify edges according to their endpoints
    for vi in range (1, len(pa)):
        p1=pa[vi][0]
        h1=pa[vi][1]
        if (h0==inside) or (h1==inside) or \
            (line.with_boundary and (h0==border) and (h1==border)):
            edge[p0]=inside
            edge[p1]=inside
        else: # outside edge --> start new polyline
            if len(edge)>0:
                edges.append(edge.keys())
                edge=OrderedDict()
        p0=p1
        h0=h1
    # add last polyline, if any    
    if len(edge)>0:
        edges.append(edge.keys())
        edge=OrderedDict()
            
    return edges

#===============================================================================
# 
# Clip the polyline at the supplied line. 
# it returns a list of polylines containing all "inside" points 
# 
def ClipPolylineListHalfspace(polylineList, line, eps=1e-8):

    pa=list()
    for polyline in polylineList:
        pa=pa+ClipPolylineHalfspace(polyline, line, eps)

    return pa

#===============================================================================
# 
# bounding box defined by two half open intervals:
#  the left and bottom boundaries are considered part of the inside,
#  right and top are outside the box 
# (for use in tiling schemes)
# 
class BoundingBox:
    def __init__(self, Xmin, Ymin, Xmax, Ymax):
        self.left=InfiniteLine2d(Xmin, Ymin, Xmin, Ymax, True)
        self.right=InfiniteLine2d(Xmax, Ymax, Xmax, Ymin, False)
        self.top=InfiniteLine2d(Xmin, Ymax, Xmax, Ymax, False)
        self.bottom=InfiniteLine2d(Xmax, Ymin, Xmin, Ymin, True)
    
#===============================================================================

def ClipPolylineBoundingBox(polyline, bbox, eps=1e-8):
    
    pl=ClipPolylineHalfspace(polyline, bbox.left, eps)
    pr=ClipPolylineListHalfspace(pl, bbox.right, eps)
    pt=ClipPolylineListHalfspace(pr, bbox.top, eps)
    return ClipPolylineListHalfspace(pt, bbox.bottom, eps)

#===============================================================================
