# copyright notice



#imports
from eoxserver.core import Component, implements, ExtensionPoint
from eoxserver.core.decoders import kvp
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)


# handler definition


class W3DSGetSceneHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    renderers = ExtensionPoint(SceneRendererInterface)

    service = "W3DS"
    versions = ["1.0"]
    request = "GetScene"

    def handle(self, request):
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

