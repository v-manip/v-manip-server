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
from __future__ import division
from eoxserver.core import Component, implements
from eoxserver.core.decoders import kvp
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)
from vmanip_server.mesh_cache import models
from django.http import HttpResponse
import json
import urllib2

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

class W3DSGetTileKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layer = kvp.Parameter()
    tilelevel = kvp.Parameter(type=int)
    tilerow = kvp.Parameter(type=int)
    tilecol = kvp.Parameter(type=int)

class W3DSGetTileHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    service = "W3DS"
    versions = ["0.4.0"]
    request = "GetTile"

    def handle(self, request):
        decoder = W3DSGetTileKVPDecoder(request.GET)
        data = self.lookup_cache(decoder)

        return (data, 'application/json');

    def lookup_cache(self, decoder):
        layer_name = decoder.layer
        tilelevel_value = decoder.tilelevel
        tilecol_value = decoder.tilecol
        tilerow_value = decoder.tilerow

        tilerow = None

        # print 'Handling: ' + layer_name + '/' + str(tilelevel_value) + '/' + str(tilecol_value) + '/' + str(tilerow_value)
  
        layer_query = models.Layer.objects.filter(name=layer_name);

        if len(layer_query):
            # print 'Found layer: ' + layer_name
            layer = layer_query[0]

            tilelevel_query = models.TileLevel.objects.filter(layer=layer.id, value=tilelevel_value)
            if len(tilelevel_query):
                # print 'Found level: ' + str(tilelevel_value) + ' for layer ' + layer_name
                tilelevel = tilelevel_query[0]

                tilecol_query = models.TileCol.objects.filter(tilelevel=tilelevel.id, value=tilecol_value)
                if len(tilecol_query):
                    # print 'Found tilecol: ' + str(tilecol_value) + ' for level ' + str(tilelevel_value)
                    tilecol = tilecol_query[0]
                    
                    tilerow_query = models.TileRow.objects.filter(tilecol=tilecol.id, value=tilerow_value)
                    if len(tilerow_query):
                        # print 'Found tilerow: ' + str(tilerow_value) + ' for col ' + str(tilecol_value)
                        tilerow = tilerow_query[0]
                    else:
                        tilerow = self.create_tilerow_record(tilecol, tilerow_value, decoder)

                else:
                    tilerow = self.create_tilecol_record(tilelevel, tilecol_value, tilerow_value, decoder)
                    print 'Created tilerow record for: ' + str(tilerow_value)
            else:
                tilerow = self.create_tilelevel_record(layer, tilelevel_value, tilecol_value, tilerow_value, decoder)
                print 'Created tilelevel record for: ' + str(tilelevel_value)
        else:
            tilerow = self.create_layer_record(layer_name, tilelevel_value, tilerow_value, tilecol_value, decoder)
            print 'Created layer record for: ' + layer_name

        if not tilerow:
            raise Exception() # FIXXME: pass to exceptionhandler
        
        # if tilelevel_value:
        #   bbox_str = self.convert_tile_params_to_scene_bbox_string(tilelevel_value, tilecol_value, tilerow_value);
        #   print 'GetScene request (' + str(tilelevel_value) + '/' + str(tilecol_value) + '/' + str(tilerow_value) + '):' + bbox_str

        # Debugging only:
        # self.get_tile_content_from_factory(decoder)

        return tilerow.content_file

    def create_layer_record(self, layer_name, tilelevel_value, tilecol_value, tilerow_value, decoder):
        content = self.get_tile_content_from_factory(decoder)

        layer = models.Layer.objects.create(name=layer_name)
        tilelevel = models.TileLevel.objects.create(layer=layer, value=tilelevel_value)
        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value, content_file=content)

        return tilerow

    def create_tilelevel_record(self, layer, tilelevel_value, tilecol_value, tilerow_value, decoder):
        content = self.get_tile_content_from_factory(decoder)

        tilelevel = models.TileLevel.objects.create(layer=layer, value=tilelevel_value)
        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        # Maybe use File.storage: https://docs.djangoproject.com/en/dev/topics/files/
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value, content_file=content)

        return tilerow

    def create_tilecol_record(self, tilelevel, tilecol_value, tilerow_value, decoder):
        content = self.get_tile_content_from_factory(decoder)

        tilecol = models.TileCol.objects.create(tilelevel=tilelevel, value=tilecol_value)
        # Maybe use File.storage: https://docs.djangoproject.com/en/dev/topics/files/
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value, content_file=content)

        return tilerow

    def create_tilerow_record(self, tilecol, tilerow_value, decoder):
        content = self.get_tile_content_from_factory(decoder)

        # Maybe use File.storage: https://docs.djangoproject.com/en/dev/topics/files/
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value, content_file=content)

        return tilerow

    def get_tile_content_from_factory(self, decoder):
        layer_value = decoder.layer
        tilelevel_value = decoder.tilelevel
        tilecol_value = decoder.tilecol
        tilerow_value = decoder.tilerow

        bbox_str = self.convert_tile_params_to_scene_bbox_string(tilelevel_value, tilecol_value, tilerow_value)
        
        # FIXXME: after a refactoring of gettyle.py into at least a separated MeshCache class the baseurl should be a parameter of this class!
        baseurl = 'http://localhost:8000/ows?service=W3DS&request=GetScene&version=1.0.0&crs=EPSG:4326&format=model/gltf'
        layer = '&layer={0}'.format(layer_value)
        bbox = '&boundingBox={0}'.format(bbox_str)
        url = baseurl + layer + bbox
        # print 'factory url: ' + (url)

        response = urllib2.urlopen(url)
        data = response.read()
        response.close()

        return data

    def convert_tile_params_to_scene_bbox_string(self, tilelevel, tilecol, tilerow):
        level_0_num_tiles_x = 4 # cols
        level_0_num_tiles_y = 2 # rows

        tile_width  = 360 / ( level_0_num_tiles_x*pow(2,tilelevel))
        tile_height = 180 / ( level_0_num_tiles_y*pow(2,tilelevel))

        # print 'tile_width  (level: ' + str(tilelevel) + ') = ' + str(tile_width)
        # print 'tile_height (level: ' + str(tilelevel) + ') = ' + str(tile_height)

        west = -180 + (tilecol*tile_width)
        east = west + tile_width
        north = 90 - (tilerow*tile_height)
        south = north - tile_height

        # from the W3DS standard draft:
        # "The value of the BoundingBox parameter is a list of comma-separated real
        # numbers in the form 'minx,miny,maxx,maxy'."
        return str(west) + ',' + str(south) + ',' + str(east) + ',' + str(north)
