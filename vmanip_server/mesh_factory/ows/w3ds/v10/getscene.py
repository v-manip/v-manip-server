# copyright notice

import pdb
import glob
#import pudb
import tempfile

#imports
from eoxserver.core import Component, implements, ExtensionPoint
from eoxserver.core.decoders import kvp, typelist, InvalidParameterException
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)
from eoxserver.resources.coverages import models
from eoxserver.services.result import ResultFile, to_http_response
from eoxserver.services.ows.wms.util import (
    lookup_layers, parse_bbox, parse_time, int_or_str
)
from eoxserver.services.subset import Subsets, Trim
from ngeo_browse_server.config.models import BrowseLayer

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import Polygon
import numpy as np
import shutil
import sys
from vmanip_server.mesh_factory.ows.w3ds.interfaces import SceneRendererInterface
from collada import *
import os
from collada_helper import trianglestrip, make_emissive_material
#import Image
from PIL import Image
import geocoord
from GeoTIFF_2_NiFTi import *
from bboxclip import clipPolylineBoundingBoxOnSphere, BoundingBox, v2dp
from uuid import uuid4
from django.conf import settings
from os.path import join

import logging


logger = logging.getLogger(__name__)


class W3DSGetSceneKVPDecoder(kvp.Decoder):
    #crs = kvp.Parameter()
    # look at getscene parameter
    boundingBox = kvp.Parameter(type=parse_bbox, num=1)
    crs = kvp.Parameter(type=str, num=1)
    layer = kvp.Parameter(type=typelist(str, ","), num=1)
    time   = kvp.Parameter(type=parse_time, num="?")
    format = kvp.Parameter(type=str, num=1)


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
        exaggeration = 10 # multiplier for curtain height in visualization

        dae_converter_path="/var/vmanip/lib/collada2gltf"
        obj_converter_path="/var/vmanip/lib/blender/blender --background --python /var/vmanip/lib/dae2obj.py -- "

        decoder = W3DSGetSceneKVPDecoder(request.GET)
        print "Layer: %s"%decoder.layer
        print "Bounding box: ", decoder.boundingBox
        print "Time from ", decoder.time.low, " to ", decoder.time.high


        base_path = '/var/vmanip/data/'
        layer = decoder.layer[0]

        try:
            bl = BrowseLayer.objects.get(pk=layer)
        except BrowseLayer.DoesNotExist:
            bl = False
        

        #print("contains curtains: %s, contains volumes: %s, format: %s"%(bl.contains_vertical_curtains, bl.contains_volumes, decoder.format))

        if layer == 'h2o_vol_demo':
            model_filename = join(base_path, 'H2O.nii.gz')
            print '[MeshFactory] delivered h2o_vol_demo product'
            return (open(model_filename,"r"), 'text/plain')
        elif layer == 'pressure_vol':
            model_filename = join(base_path, 'Pressure.nii.gz')
            print '[MeshFactory] delivered pressure_vol_demo product'
            return (open(model_filename,"r"), 'text/plain')
        elif layer == 'temperature_vol':
            model_filename = join(base_path, 'Temperature.nii.gz')
            print '[MeshFactory] delivered temperature_vol_demo product'
            return (open(model_filename,"r"), 'text/plain')

        TextureResolutionPerTile = 256
        GeometryResolutionPerTile = 16
        MaximalCurtainsPerResponse = 32

        output_dir=tempfile.mkdtemp(prefix='tmp_meshfactory_')
        print "creating %s"%output_dir

        # create new collada scene
        mesh = Collada()

        geom_nodes=[] # list for all the curtain parts

        # debug response generation!
        response = []
        result_set = []

        bbox=Polygon.from_bbox(tuple(decoder.boundingBox))
        mybbox=BoundingBox(decoder.boundingBox[0], decoder.boundingBox[1], decoder.boundingBox[2], decoder.boundingBox[3])
        # use a minimal step size of (diagonal of bbox) / GeometryResolutionPerTile
        minimalStepSize = v2dp(decoder.boundingBox[0], decoder.boundingBox[1], 0.0).great_circle_distance(
            v2dp(decoder.boundingBox[2], decoder.boundingBox[3], 0.0)) / GeometryResolutionPerTile
        #response.append( "minimal step size: %6.4f<br>" % minimalStepSize )

        timesubset = Subsets([Trim("t", decoder.time.low, decoder.time.high)]) # trim to requested time interval

        if bl and bl.contains_vertical_curtains:
            print "Curtain creation"
            # iterate over all "curtain" coverages
            for l in decoder.layer:
                layer = models.DatasetSeries.objects.get(identifier=l)
                
                #pdb.set_trace()

                for coverage in timesubset.filter(models.CurtainCoverage.objects.filter(collections__in=[layer.pk]).filter(footprint__intersects=bbox)):

                    logger.info('Creating Curtain data for coverage: %s' % (coverage.identifier,))

                    # write the ID of the coverage
                    response.append("%s: " % coverage.identifier)

                    # retrieve the data item pointing to the raster data
                    raster_item = coverage.data_items.get(
                        semantic__startswith="bands"
                    )

                    in_name=raster_item.location        # texture file name
                    # construct the texture names for conversion
                    name=str(uuid4()) # generate a REALLY unique identifier
                    
                    out_name=os.path.join(output_dir, name+'.png')
                    textureImage = Image.open(in_name)
    #                textureImage = Image.open('/vagrant/shares/data/UV_map.png') # debug texture
                    print "Texture="+in_name
                    (width, height) = textureImage.size
                    if textureImage.mode == 'F':  # still a float image: (we expect 8bit)
                        # map a subrange of a float image to an 8 bit PNG
                        i = np.array(list(textureImage.getdata())).reshape(textureImage.size[::-1])
                        g = np.divide(np.subtract(i, min_level), (max_level - min_level) / 255.0)
                        g[g < 0] = 0
                        textureImage = Image.fromarray(g.astype(np.uint8), 'L')

                    # open it with GDAL to get the width/height of the raster
                    # ds = gdal.Open(raster_item.location)
                    # width=ds.RasterXSize
                    # height=ds.RasterYSize

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
                    #print "%d coordinates (Xmin: %d, Xmax: %d, Ymin: %d, Ymax: %d), %d height levels (min: %d, max: %d)<br/>" % (len(gcps), X.min(), X.max(), Y.min(), Y.max(), len(height_values), heightLevelsList.min(), heightLevelsList.max())

                    # now build the geometry:

                    # stuff curtain piece footprint in polyline
                    polyline=list()
                    [x, y, u, v]  = gcps[0]
                    previous_position = v2dp(x, y, u)
                    polyline.append(v2dp(x, y, u))  # insert first ColRow entry
                    for [x, y, u, v] in gcps[1:-1]:  # loop over inner ColRows
                        position = v2dp(x, y, u)
                        if position.great_circle_distance(previous_position) >= minimalStepSize:
                            polyline.append(position)  # append only ColRows with minimal step size
                            previous_position = position
                    #[u, v, x, y] = UVXY[-1]
                    [x, y, u, v]  = gcps[-1]
                    polyline.append(v2dp(x, y, u))  # insert last ColRow entry
                    #print "- %d nodes, length curtain = %6.3f" % (
                    #    len(polyline), polyline[0].great_circle_distance(polyline[-1]))

                     # clip curtain on bounding box
                    polylist=clipPolylineBoundingBoxOnSphere(polyline, mybbox)

                    u_min = sys.float_info.max
                    u_max = -sys.float_info.max
                    #print " width=%d"%width
                    if len(polylist)>0:
                        # create a unique material for each texture
                        matnode = make_emissive_material(mesh, "Material-"+name, name+".png")
                        # determine texture coordinate U range
                        for pl in polylist:
                            if len(pl)>0:
                                # now build the geometry
                                t=trianglestrip()
                                for p in pl:
                                    u = p.u
                                    u_min = min (u_min, u)
                                    u_max = max (u_max, u)

                        #print "U: min=%f, max=%f"%(u_min, u_max)
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
                                        u = ((p.u - u_min)/ u_scale)  # normalize u to range [0,1]
                                        print ("U(%5.2f %5.2f) X, Y=(%5.2f,%5.2f), " % (p.u, u, x, y))
                                        point = geocoord.fromGeoTo3D(np.array((x, y, heightLevelsList.min())))
                                        t.add_point(point, [u, 0], [0, 0, 1])
                                        point = geocoord.fromGeoTo3D(np.array((x, y, heightLevelsList.max() * exaggeration)))
                                        t.add_point(point, [u, 1], [0, 0, 1])
                                    n=n+1
                                    # put everything in a geometry node
                                    geomnode = t.make_geometry(mesh, "Strip-%d-" % n + name,
                                                                # return time interval as meta data appended in geometry id
                                                               "%s-%s_%s"%(name, coverage.begin_time.isoformat(), coverage.end_time.isoformat()),
                                                               matnode)  # all these pieces have the same material
                                    geom_nodes.append(geomnode)

                        # now crop the image to the resolution we need:
                        textureImage = textureImage.crop((int(round(u_min)), 0, int(round(u_max)) + 1, height))

                        # and resize it to the maximum allowed tile size
                        (width, height) = textureImage.size
                        if width > TextureResolutionPerTile:
                            height = float(height) * float(TextureResolutionPerTile) / float(width)
                            width = float(TextureResolutionPerTile)

                        if height > TextureResolutionPerTile:
                            height = float(TextureResolutionPerTile)
                            width = float(width) * float(TextureResolutionPerTile) / float(height)

                        textureImage = textureImage.resize((int(round(width)), int(round(height))), Image.ANTIALIAS)
                        textureImage.save(out_name, "PNG")
                        print 'texture %s resized to w=%5.2f h=%5.2f'%(out_name, width, height)

            # put all the geometry nodes in a scene node
            node = scene.Node("node0", children=geom_nodes)
            myscene = scene.Scene("myscene", [node])
            mesh.scenes.append(myscene)
            mesh.scene = myscene

            id = str(uuid4())
            out_file_dae=os.path.join(output_dir, id + '.dae')
            out_file_gltf=os.path.join(output_dir, id + '.json')
            out_file_obj=os.path.join(output_dir, id + '.obj')
            
            # now write the collada file to a temporary location
            mesh.write(out_file_dae)
            
            ##print("Format = '%s'"%decoder.format)
            logger.info('Creating response data for curtain in format: %s' % (decoder.format,))
            
            if decoder.format == "model/obj":
                # and convert it to obj
                converter_output=os.popen(obj_converter_path+out_file_dae+" "+out_file_obj).read()
                print("convert from %s to %s:"%(out_file_dae, out_file_obj))
            else:
                # or convert it to glTF
                converter_output=os.popen(dae_converter_path+" -f "+out_file_dae+" -o "+out_file_gltf).read()
                print("convert from %s to %s:"%(out_file_dae, out_file_gltf))
            
            print converter_output

            #pdb.set_trace()
            #response.append(converter_path+" -f "+out_file_dae+" -o "+out_file_gltf)
            #response.append("<h3>converter output</h3><pre>")
            #response.append(converter_output+"</pre>")
            os.remove(out_file_dae) # we do not need the collada file anymore

            # now put all files generated by the converter in the multipart response
            outfiles = glob.glob(output_dir + '/*.*')

            for of in outfiles:
                print "attaching file: ", of

                contenttype = ""
                if of.endswith('.obj'):
                    contenttype = "model/obj"
                elif of.endswith('.mtl'):
                    contenttype = "text/plain"
                elif of.endswith('.png'):
                    contenttype = "image/png"
                else:
                    contenttype = "application/octet-stream"

                result_set.append(ResultFile(of, filename=os.path.split(of)[1], content_type=contenttype))

            logger.info('Returning curtain response')
            response=to_http_response(result_set)


        elif bl and bl.contains_volumes:
            print "Volumes!"
            # iterate over all "volume" coverages
            result = []
            for l in decoder.layer:
                layer = models.DatasetSeries.objects.get(identifier=l)
                
                #pdb.set_trace()

                for coverage in timesubset.filter(models.CubeCoverage.objects.filter(collections__in=[layer.pk]).filter(footprint__intersects=bbox)):
                #for coverage in models.CubeCoverage.objects.filter(collections__in=[layer.pk]).filter(footprint__intersects=bbox):

                    # retrieve the data item pointing to the raster data
                    raster_item = coverage.data_items.get(
                        semantic__startswith="bands"
                    )
                    in_name=raster_item.location        # texture file name

                    print("ID=%s, Name=%s " % (coverage.identifier, in_name))

                    
                    id = str(uuid4())
                    out_file_nii=os.path.join(output_dir, id + '.nii.gz')
                    convert_GeoTIFF_2_NiFTi(coverage, in_name, out_file_nii, decoder.boundingBox, decoder.crs)
                    #pdb.set_trace()
                    result.append(ResultFile(out_file_nii, content_type='application/x-nifti'))

            response = to_http_response(result)

        elif decoder.format == "model/nii-gz":
            print "2D Volume creation"
            # iterate over all "volume" coverages
            result = []
            for l in decoder.layer:
                layer = models.DatasetSeries.objects.get(identifier=l)
                
                coverage_collection = []

                id = str(uuid4())
                out_file_nii=os.path.join(output_dir, id + '.nii.gz')

                for coverage in timesubset.filter(models.RectifiedDataset.objects.filter(collections__in=[layer.pk]).filter(footprint__intersects=bbox)):

                    #retrieve the data item pointing to the raster data
                    raster_item = coverage.data_items.get(
                        semantic__startswith="bands"
                    )
                    in_name=raster_item.location        # texture file name
                    coverage_collection.append((coverage, in_name))

                convert_collection_GeoTIFF_2_NiFTi(coverage_collection, out_file_nii, decoder.boundingBox, decoder.crs)
                result.append(ResultFile(out_file_nii, content_type='application/x-nifti'))

            response = to_http_response(result)



        print "removing %s"%output_dir
        shutil.rmtree(output_dir) # remove temp directory
        
        return response # return response
            
