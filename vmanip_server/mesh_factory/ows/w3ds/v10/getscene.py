# copyright notice



#imports
from eoxserver.core import Component, implements, ExtensionPoint
from eoxserver.core.decoders import kvp
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)
from eoxserver.resources.coverages import models

from vmanip_server.mesh_factory.ows.w3ds.interfaces import SceneRendererInterface


# handler definition


class W3DSGetSceneHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    renderers = ExtensionPoint(SceneRendererInterface)

    service = "W3DS"
    versions = ["1.0"]
    request = "GetScene"

    def handle(self, request):

        # The following code is *not* actually related to W3DS "GetScene" but
        # shall demonstrate the use of the curtain coverages and its associated
        # data and metadata.

        # For data/metadata extraction
        import json
        from eoxserver.contrib import gdal

        # really basic response generation!
        response = []


        # iterate over all "curtain" coverages
        for coverage in models.CurtainCoverage.objects.all():
            # write the ID of the coverage
            response.append("<h1>%s</h1>" % coverage.identifier)

            # retrieve the data item pointing to the raster data
            raster_item = coverage.data_items.get(
                semantic__startswith="bands"
            )

            # open it with GDAL to get the width/height of the raster
            ds = gdal.Open(raster_item.location)

            response.append("Width: %d <br/>" % ds.RasterXSize)
            response.append("Height: %d <br/>" % ds.RasterYSize)

            # retrieve the data item pointing to the height values/levels
            height_values_item = coverage.data_items.get(
                semantic__startswith="heightvalues"
            )

            # load the json file to a list
            with open(height_values_item.location) as f:
                height_values = json.load(f)

            # write out the height levels
            response.append("Height levels (count: %d):<br/>" % len(height_values))
            response.append("<ul>")
            for height_value in height_values:
                response.append("<li>%f</li>" % height_value)
            response.append("</ul>")
            
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



class W3DSGetSceneKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layers = kvp.Parameter(type=typelist(",", str))
    # look at getscene parameter

    '''

