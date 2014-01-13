#-------------------------------------------------------------------------------
#
# Project: V-MANIP Server <http://v-manip.eox.at>
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2012 EOX IT Services GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------



#imports
from eoxserver.core import Component, implements
from eoxserver.core.decoders import kvp
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)
from vmanip_server.mesh_cache import models
from django.http import HttpResponse
import json

# KVP decoder

class W3DSGetTileKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layer = kvp.Parameter()
    tilelevel = kvp.Parameter(type=int)
    tilerow = kvp.Parameter(type=int)
    tilecol = kvp.Parameter(type=int)

# handler definition

class W3DSGetTileHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    service = "W3DS"
    versions = ["0.4.0"]
    request = "GetTile"

    def handle(self, request):
        data = self.lookup_cache('adm_aeolus', 1, 0, 0)

        # FIXXME: error handling
        # if not data:
        #   self.handleError()
        
        return (json.dumps(data), 'application/json');

    def loadJSONFromFile(self, filename):
        # json_data = open('static/answer.json')
        json_data = open(filename)
        data = json.load(json_data) # deserialize it
        json_data.close()
        return data

    def lookup_cache(self, layer_name, tilelevel_value, tilecol_value, tilerow_value):
        tilerow = None

        print 'Handling: ' + layer_name + '/' + str(tilelevel_value) + '/' + str(tilecol_value) + '/' + str(tilerow_value)

        # FIXXME: When a layer is created for the first time it can be created multiple times, because
        # the WebClient sends 4 parallel requests. The 'result' will be 0 for each of the 4 requests, therefore
        # the new layer will get created in the database 4 times.
        # The current workaround is to manually create the layer table upfront, but this has to be fixed!          
        layer_query = models.Layer.objects.filter(name=layer_name);

        if len(layer_query):
            print 'Found layer: ' + layer_name
            if len(layer_query) != 1:
                print 'Error! There should only be one entry for each layer!'
            layer = layer_query[0]

            tilelevel_query = models.TileLevel.objects.filter(layer=layer.id, value=tilelevel_value);
            if len(tilelevel_query):
                print '0'
                print 'Found level: ' + str(tilelevel_value) + ' for layer ' + layer_name
                if len(layer_query) != 1:
                    print 'Error! There should only be one entry for each level!'
                tilelevel = tilelevel_query[0]

                tilecol_query = models.TileCol.objects.filter(tilelevel=tilelevel.id, value=tilecol_value);
                if len(tilecol_query):
                    print '1'
                    print 'Found tilecol: ' + str(tilecol_value) + ' for level ' + str(tilelevel_value)
                    if len(tilecol_query) != 1:
                        print 'Error! There should only be one entry for each tilecol!'
                    tilecol = tilecol_query[0]
                    
                    tilerow_query = models.TileRow.objects.filter(tilecol=tilecol.id, value=tilerow_value);
                    if len(tilerow_query):
                        print '2'
                        print 'Found tilerow: ' + str(tilerow_value) + ' for col ' + str(tilecol_value)
                        if len(tilerow_query) != 1:
                            print 'Error! There should only be one entry for each tilerow!'
                        tilerow = tilerow_query[0]
                else:
                    tilerow = self.create_tilecol_record(tilelevel, tilecol_value, tilerow_value)
                    print '3'                    
                    print 'Created tilerow record for: ' + str(tilerow_value)
            else:
                tilerow = self.create_tilelevel_record(layer, tilelevel_value, tilecol_value, tilerow_value)
                print '4'
                print 'Created tilelevel record for: ' + str(tilelevel_value)
        else:
            tilerow = self.create_layer_record(layer_name, tilelevel_value, tilerow_value, tilecol_value)
            print '5'
            print 'Created layer record for: ' + layer_name

            print 'tilerow:'
            print tilerow

        #print 'tilerow_content: ' + tilerow.content_file

        #content = self.loadJSONFromFile(tilerow.content_file)
        #return content
        return "asdf"

    def create_layer_record(self, layer_name, tilelevel_value, tilecol_value, tilerow_value):
        layer = models.Layer.objects.create(name=layer_name)
        tilelevel = models.TileLevel.objects.create(layer=layer, value=tilelevel_value)
        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value)

        # FIXXME: Request from MeshFactory!
        tilerow.content_file = 'models/curtain_test/answer.json'

        return tilerow

    def create_tilelevel_record(self, layer, tilelevel_value, tilecol_value, tilerow_value):
        tilelevel = models.TileLevel.objects.create(layer=layer, value=tilelevel_value)
        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value)

        # FIXXME: Request from MeshFactory!
        tilerow.content_file = 'models/curtain_test/answer.json'

        return tilerow

    def create_tilecol_record(self, tilelevel, tilecol_value, tilerow_value):
        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value)

        # FIXXME: Request from MeshFactory!
        tilerow.content_file = 'models/curtain_test/answer.json'

        return tilerow

    def create_tilerow_record(self, tilecol, tilerow_value):
        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value)

        # FIXXME: Request from MeshFactory!
        tilerow.content_file = 'models/curtain_test/answer.json'

        return tilerow

        '''# request is a Django HTTPRequest object

        if error:
            raise Exception() # should be passed to the exceptionhandler

        # NEVER! do this:
        # self.something = something

        # response is either a django HTTPResponse, a string or a tuple (content, content-type), (content, content-type, status-code)


        # attention, pseudo code

        decoder = W3DSGetTileKVPDecoder(request.GET)

        tile = self.lookup_cache(decoder.layer, decoder.tilelevel, decoder.tilerow, decoder.tilecol)

        if not tile:
            #either return empty response, raise exception or proxy to mesh factory
            

        return response 
    '''
