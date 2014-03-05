# -*- coding: latin-1 -*-

from collections import namedtuple
from math import hypot, fabs, sin, cos, radians, sqrt, atan2
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

    def great_circle_distance(self, other):
        diff_lat = radians(other.x - self.x)
        diff_long = radians(other.y - self.y)
        a = (sin(diff_lat / 2) * sin(diff_lat / 2) +
             cos(radians(self.x)) * cos(radians(other.x)) *
             sin(diff_long / 2) * sin(diff_long / 2))
        return 2 * atan2(sqrt(a), sqrt(1 - a))

    def abs(self):
        return self.distance_to(type(self)(0.0, 0.0, 0.0))

    def __repr__(self):
        return "[%5.2f, %5.2f] (%5.2f)" % (self.x, self.y, self.u)


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
        self.normal = v2dp(y2 - y1, x1 - x2, 0)
        self.normal = self.normal / self.normal.abs()
        self.with_boundary = with_boundary
        self.offset = 0
        self.offset = self.distance(v2dp(x1, y1, 0))

    def distance(self, point):
        return self.normal.dot(point) - self.offset


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
def clipPolylineHalfspace(polyline, line, eps=1e-8):
    # constants for point classification
    inside = 1
    outside = 2
    border = 3

    pa = []  # intermediate polyline
    # first pass: add intersection points and classify all points
    for vi in range(0, len(polyline)):
        p1 = polyline[vi]
        h1 = line.distance(p1)
        h1p = h1 > eps
        h1n = h1 < -eps
        if (vi > 0) and ((h0p and h1n) or (h0n and h1p)):  # points are on opposite sides:
            # noinspection PyUnboundLocalVariable
            pn = (p0 + (p1 - p0) * (h0 / (h0 - h1)))  # clip segment
            pa.append((pn, border))  # insert new point in intermediate poly

        # mark points appropriately
        if h1p:
            pa.append((p1, inside))
        elif h1n:
            pa.append((p1, outside))
        else:
            pa.append((p1, border))
        h0p = h1p
        h0n = h1n
        p0 = p1
        h0 = h1

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

    edges = list()
    edge = OrderedDict()
    p0 = pa[0][0]
    h0 = pa[0][1]

    # 2nd pass: classify edges according to their endpoints
    for vi in range(1, len(pa)):
        p1 = pa[vi][0]
        h1 = pa[vi][1]
        if (h0 == inside) or (h1 == inside) or \
                (line.with_boundary and (h0 == border) and (h1 == border)):
            edge[p0] = inside
            edge[p1] = inside
        else:  # outside edge --> start new polyline
            if len(edge) > 0:
                edges.append(edge.keys())
                edge = OrderedDict()
        p0 = p1
        h0 = h1
    # add last polyline, if any
    if len(edge) > 0:
        edges.append(edge.keys())

    return edges


#===============================================================================
#
# Clip the polyline at the supplied line.
# it returns a list of polylines containing all "inside" points
#
def clipPolylineListHalfspace(polylineList, line, eps=1e-8):
    pa = list()
    for polyline in polylineList:
        pa = pa + clipPolylineHalfspace(polyline, line, eps)

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
        self.left = InfiniteLine2d(Xmin, Ymin, Xmin, Ymax, True)
        self.right = InfiniteLine2d(Xmax, Ymax, Xmax, Ymin, False)
        self.top = InfiniteLine2d(Xmin, Ymax, Xmax, Ymax, False)
        self.bottom = InfiniteLine2d(Xmax, Ymin, Xmin, Ymin, True)


#===============================================================================
#
# clips the supplied polyline (v2dp list) on the bounding box
# guarantees that points within eps of a boundary are consistently clipped (see above)
#
def clipPolylineBoundingBox(polyline, bbox, eps=1e-8):
    pl = clipPolylineHalfspace(polyline, bbox.left, eps)
    pr = clipPolylineListHalfspace(pl, bbox.right, eps)
    pt = clipPolylineListHalfspace(pr, bbox.top, eps)
    return clipPolylineListHalfspace(pt, bbox.bottom, eps)


#===============================================================================
#
# correctly handles wraparound of x-coordinates at ±wrap_at:
#        a polyline segment going from -X to +X with a difference >wrap_at is
#        handled as straddling the X=±wrap_at boundary (e.g. the 180th meridian)
# returns a list of polylines guaranteed to NOT cross the wrap_at line
#
def clipPolylineOnWrap(polyline, wrap_at=180, eps=1e-8):
    polylist = list()
    newline = list()
    po = polyline.pop(0)
    newline.append(po)
    for pn in polyline:
        if (pn.x * po.x < 0.0) and (fabs(pn.x - po.x) > wrap_at):  # segment straddles wraparound
            if po.x < pn.x:  # check from which side we come
                # coming from -X: (po<0, pn>0)
                ponew = po + v2dp(wrap_at * 2.0, 0.0, 0.0)  # move po into +X
                pnnew = pn + v2dp(-wrap_at * 2.0, 0.0, 0.0)  # move pn into -X
            else:  # coming from +X: (pn<0, po>0)
                ponew = po + v2dp(-wrap_at * 2.0, 0.0, 0.0)  # move po into -X
                pnnew = pn + v2dp(wrap_at * 2.0, 0.0, 0.0)  # move pn into +X

            ho = wrap_at - fabs(po.x)  # distance po to wrap_at line
            hn = wrap_at - fabs(pn.x)  # distance pn to wrap_at line

            if (ho + hn) < eps:  # both points on the wrap_at line
                factor = 0.5  # just put it in the middle
            else:
                factor = (ho / (ho + hn))

            # intersection points with wrap_at:
            IPn = (ponew + (pn - ponew) * factor)  # positive side
            IPo = (po + (pnnew - po) * factor)  # negative side
            newline.append(IPo)
            po = IPo
            polylist.append(newline)
            newline = list()
            newline.append(IPn)
        newline.append(pn)
        po = pn

    polylist.append(newline)
    return polylist


#===============================================================================
#
# clips the supplied polyline (v2dp list) on the bounding box
# guarantees that points within eps of a boundary are consistently clipped (see above)
# additionally correctly handles wraparound of x-coordinates at ±wrap_at
#        (e.g. the 180th meridian)
#
def clipPolylineBoundingBoxOnSphere(polyline, bbox, wrap_at=180, eps=1e-8):
    pw = clipPolylineOnWrap(polyline, wrap_at, eps)
    pl = clipPolylineListHalfspace(pw, bbox.left, eps)
    pr = clipPolylineListHalfspace(pl, bbox.right, eps)
    pt = clipPolylineListHalfspace(pr, bbox.top, eps)
    return clipPolylineListHalfspace(pt, bbox.bottom, eps)

#===============================================================================
