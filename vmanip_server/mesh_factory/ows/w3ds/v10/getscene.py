# copyright notice



#imports
from eoxserver.core import Component, implements, ExtensionPoint
from eoxserver.core.decoders import kvp
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)


from vmanip_server.mesh_factory.ows.w3ds.interfaces import SceneRendererInterface
import json

class W3DSGetSceneKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layer = kvp.Parameter()

# handler definition


class W3DSGetSceneHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    renderers = ExtensionPoint(SceneRendererInterface)

    service = "W3DS"
    versions = ["1.0.0"]
    request = "GetScene"

    def handle(self, request):
        decoder = W3DSGetSceneKVPDecoder(request.GET)
        model_filename = None
        data_is_json = True

        if (decoder.layer == 'vrvis_demo'):
            model_filename = 'products/vrvis_demo/vrvis_demo.json'
            # print '[MeshFactory] delivered vrvis_demo product'
        elif (decoder.layer == 'eox_demo'):
            model_filename = 'products/eox_demo/eox_demo.json'
            # print '[MeshFactory] delivered eox_demo product'
        elif (decoder.layer == 'h2o_vol_demo'):
            model_filename = 'products/h2o_vol_demo/H2O.nii.gz'
            data_is_json = False
            print '[MeshFactory] delivered h2o_vol_demo product'
        elif (decoder.layer == 'pressure_vol'):
            model_filename = 'products/pressure_vol_demo/Pressure.nii.gz'
            data_is_json = False
            print '[MeshFactory] delivered pressure_vol_demo product' 
        elif (decoder.layer == 'temperature_vol'):
            model_filename = 'products/temperature_vol_demo/Temperature.nii.gz'
            print '[MeshFactory] delivered temperature_vol_demo product'

        if model_filename:
            if data_is_json:
                data = self.load_json_from_file(model_filename)
                return (data, 'application/json')
            else:
                return (open(model_filename), 'model/nii-gz')
        else:
            print 'ERROR: NO PRODUCT WITH NAME ' + decoder.layer + ' FOUND!'
            return ('{ "errorText": "No product with id ' + decoder.layer + ' available" }', 'application/json')


        # print 'GetScene: filename = ', model_filename

        # if data_is_json:
        #     data = self.load_json_from_file(model_filename)
        #     return (json.dumps(data), 'application/json')
        # else:
        #     data = open(model_filename)
        #     return (data, 'application/nii-gz')


    def load_json_from_file(self, filename):
        try:
            json_data = open(filename)
            data = json.load(json_data) # deserialize it
            json_data.close()
        except:
            print '[MeshFactory] file: "' + filename + '"" not readable'
        return json.dumps(data)

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

