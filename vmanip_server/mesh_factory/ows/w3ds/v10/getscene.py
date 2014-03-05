# copyright notice

import pdb
#import pudb

#imports
from eoxserver.core import Component, implements, ExtensionPoint
from eoxserver.core.decoders import kvp, typelist, InvalidParameterException
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)
from eoxserver.resources.coverages import models
from eoxserver.services.ows.wms.util import (
    lookup_layers, parse_bbox, parse_time, int_or_str
)
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import Polygon
import numpy as np
import sys
from vmanip_server.mesh_factory.ows.w3ds.interfaces import SceneRendererInterface
from collada import *
import os
from collada_helper import trianglestrip, make_emissive_material
from PIL import Image
import geocoord
from bboxclip import ClipPolylineBoundingBoxOnSphere, BoundingBox, v2dp

# map a subrange of a float image to an 8 bit PNG
# and write it to disk
#
#  returns size of image
def mapimage(infile, outfile, lmin, lmax):
    im = Image.open(infile)
    i=np.array(list(im.getdata())).reshape(im.size[::-1])
    g=np.divide(np.subtract(i,lmin), (lmax-lmin)/255.0)
    g[g<0]=0
    iout=Image.fromarray(g.astype(np.uint8), 'L')
    iout.save(outfile, "PNG")
    return im.size

class W3DSGetSceneKVPDecoder(kvp.Decoder):
    #crs = kvp.Parameter()
    #layers = kvp.Parameter(type=typelist(",", str))
    bbox = kvp.Parameter(type=parse_bbox, num=1)
    # look at getscene parameter

# handler definition


class W3DSGetSceneHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    renderers = ExtensionPoint(SceneRendererInterface)

    service = "W3DS"
    versions = ["1.0"]
    request = "GetScene"

    def handle(self, request):

        # For data/metadata extraction
        import json
        from eoxserver.contrib import gdal

        min_level = -40 # maps to 0 in output texture
        max_level =  50 # maps to 255 in output texture
        exaggeration = 40 # multiplier for curtain height in visualization
        output_dir="/var/data/glTF"
        converter_path="/vagrant/shares/lib/collada2gltf"
        
        decoder = W3DSGetSceneKVPDecoder(request.GET)
        TextureResolutionPerTile = 256
        GeometryResolutionPerTile = 16
        MaximalCurtainsPerResponse = 32


        if not os.path.exists(output_dir):
            os.makedirs(output_dir)


        # create new collada scene
        mesh = Collada()

        geom_nodes=[] # list for all the curtain parts

        # debug response generation!
        response = []


        #bbox=Polygon.from_bbox((31, -60, 37, -40))
        bbox=Polygon.from_bbox(tuple(decoder.bbox))
        mybbox=BoundingBox(decoder.bbox[0], decoder.bbox[1], decoder.bbox[2], decoder.bbox[3])
        # use a minimal step size of (diagonal of bbox) / GeometryResolutionPerTile
        #minimalStepSize = great circle diagonal of bbox / GeometryResolutionPerTile
        minimalStepSize = v2dp(decoder.bbox[0], decoder.bbox[1], 0.0).great_circle_distance(v2dp(decoder.bbox[2], decoder.bbox[3], 0.0)) / GeometryResolutionPerTile
        response.append( "minimal step size: %6.4f<br>" % minimalStepSize )

        # iterate over all "curtain" coverages
        #for coverage in models.CurtainCoverage.objects.all():
        for coverage in models.CurtainCoverage.objects.filter(footprint__intersects=bbox):

            # write the ID of the coverage
            response.append("%s: " % coverage.identifier)
            print coverage

            # retrieve the data item pointing to the raster data
            raster_item = coverage.data_items.get(
                semantic__startswith="bands"
            )

            in_name=raster_item.location        # texture file name
            # construct the texture names for conversion
            #basename=os.path.basename(in_name)
            (name, _) =os.path.splitext(os.path.basename(in_name)) # generate a unique identifier
            out_name=os.path.join(output_dir, name+'.png')
            #response.append("Input file: %s<br>" % raster_item.location)
            #response.append("Output file: %s<br>" % out_name)
            #response.append("ID: %s<br>" % name)
            # map range of texture and convert to png
            (width, height)=mapimage(in_name, out_name, min_level, max_level)

            # open it with GDAL to get the width/height of the raster
            # ds = gdal.Open(raster_item.location)
            # width=ds.RasterXSize
            # height=ds.RasterYSize

            #response.append("image width: %d, height: %d<br/>" % (width, height))

            # retrieve the data item pointing to the height values/levels
            height_values_item = coverage.data_items.get(
                semantic__startswith="heightvalues"
            )

            # retrieve the data item pointing to the coordinates
            gcps_item = coverage.data_items.get(
                semantic__startswith="gcps"
            )


            # load the json files to lists
            with open(height_values_item.location) as f:
                height_values = json.load(f)
            heightLevelsList=np.array(height_values)

            with open(gcps_item.location) as f:
                gcps = json.load(f)

            coords=np.array(gcps)
            X=coords[:,0]
            Y=coords[:,1]
            # write out the coordinates
            response.append("%d coordinates (Xmin: %d, Xmax: %d, Ymin: %d, Ymax: %d), %d height levels (min: %d, max: %d)<br/>" % (len(gcps), X.min(), X.max(), Y.min(), Y.max(),len(height_values), heightLevelsList.min(), heightLevelsList.max()))
            # create a unique material for each texture
            matnode = make_emissive_material(mesh, "Material-"+name, name+".png")

            # now build the geometry
            #pdb.set_trace()

            # stuff curtain piece footprint in polyline
            polyline=list()
            UVXY = np.hstack((colRowList, coordList))
            print "length=%d nodes, " % UVXY.shape[0],
            # noinspection PyRedeclaration
            [u, v, x, y] = UVXY[0]
            previous_position = v2dp(x, y, u)
            polyline.append(v2dp(x, y, u))  # insert first ColRow entry
            for [u, v, x, y] in UVXY[1:-1]:  # loop over inner ColRows
                position = v2dp(x, y, u)
                if position.great_circle_distance(previous_position) >= minimalStepSize:
                    polyline.append(position)  # append only ColRows with minimal step size
                    previous_position = position
            [u, v, x, y] = UVXY[-1]
            polyline.append(v2dp(x, y, u))  # insert last ColRow entry
            print "- %d nodes, length curtain = %6.3f" % (len(polyline), polyline[0].great_circle_distance(polyline[-1]))

             # clip curtain on bounding box
            polylist=ClipPolylineBoundingBoxOnSphere(polyline, mybbox)

            u_min = sys.float_info.max
            u_max = -sys.float_info.max
            print " width=%d"%width
            if len(polylist)>0:
                # determine texture coordinate U range
                for pl in polylist:
                    if len(pl)>0:
                        # now build the geometry
                        t=trianglestrip()
                        for p in pl:
                            u=p.u / (width+1) # this is not correct, need to be in the middle of the texel
                            u_min = min (u_min, u)
                            u_max = max (u_max, u)

                response.append("U: min=%f, max=%f<br>"%(u_min, u_max))
                u_scale=u_max-u_min
                # convert all clipped polylines to triangle strips
                n=0
                if (u_scale>sys.float_info.min):
                    for pl in polylist:
                        if len(pl)>0:
                            # now build the geometry
                            t=trianglestrip()
                            for p in pl:
                                x=p.x
                                y=p.y
                                u=p.u / (width+1) / u_scale + u_min # this is not correct, need to be in the middle of the texel
                                response.append("U(%5.2f %5.2f) X, Y=(%5.2f,%5.2f), "%(p.u, u, x, y))
                                point=geocoord.fromGeoTo3D(np.array((x, heightLevelsList.min(), y)))
                                t.add_point(point, [u, 0], [0, 0, 1])
                                point=geocoord.fromGeoTo3D(np.array((x, heightLevelsList.max()*exaggeration, y)))
                                t.add_point(point, [u, 1], [0, 0, 1])
                            n=n+1
                            # put everything in a geometry node
                            geomnode=t.make_geometry(mesh, "Strip-%d-"%n+name, matnode) # all these pieces have the same material
                            geom_nodes.append(geomnode)

            #pdb.set_trace()

        # put all the geometry nodes in a scene node
        node = scene.Node("node0", children=geom_nodes)
        myscene = scene.Scene("myscene", [node])
        mesh.scenes.append(myscene)
        mesh.scene = myscene

        out_file_dae=os.path.join(output_dir, 'test.dae')
        out_file_gltf=os.path.join(output_dir, 'test.gltf')
        # now write the collada file to a temporary location
        mesh.write(out_file_dae)

        # and convert it to glTF
        converter_output=os.popen(converter_path+" -f "+out_file_dae+" -o "+out_file_gltf).read()
        response.append(converter_path+" -f "+out_file_dae+" -o "+out_file_gltf)
        response.append("<h3>converter output</h3><pre>")
        response.append(converter_output+"</pre>")

        return "".join(response)


        #return "\n".join(map(lambda c: c.identifier, models.CurtainCoverage.objects.all()))
        #return """Response for GetScene Request"""

        '''
        # Pseudocode
        # request is a Django HTTPRequest object

        if error:
            raise Exception() # should be passed to the exceptionhandler

        # attention, pseudo code

        decoder = W3DSGetSceneKVPDecoder(request.GET)

        layers = decoder.layers

        scene = Scene()


        renderer = get_renderer(request)

        coverages = []
        for layer in layers:
            # retrieve coverage from DB
            coverages.append(models.Coverage.objects.get(identifier=layer))

        parameters = {
            "bbox": ...
            "minheight": ..

        }
        renderer.render_scene(coverages, parameters)





        # encode "scene" according to decoder.format
        encoder = self.get_scene_renderer(decoder.format)
        return encoder.encode_scene(scene), encoder.content_type

    def get_scene_renderer(self, format):
        for renderer in self.renderers:
            if format in renderer.formats:
                return renderer

        raise Exception("Format %s not supported" % format)




    '''

