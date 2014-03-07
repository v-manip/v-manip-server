#-------------------------------------------------------------------------------
#
# Project: V-MANIP Server <http://v-manip.eox.at>
# Authors: Martin Hecher <martin.hecher@fraunhofer.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 Fraunhofer Austria GmbH
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

from __future__ import division
from vmanip_server.mesh_cache import models
from vmanip_server.mesh_cache import mapcache

from eoxserver.core.decoders import kvp
from django.http import HttpResponse
import json
import urllib2

class W3DSGetTileKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layer = kvp.Parameter()
    time = kvp.Parameter()
    tilelevel = kvp.Parameter(type=int)
    tilerow = kvp.Parameter(type=int)
    tilecol = kvp.Parameter(type=int)


class MeshCache:
    def lookup_request(self, request):
        decoder = W3DSGetTileKVPDecoder(request.GET)

        layer_name = decoder.layer
        tilelevel_value = decoder.tilelevel
        tilecol_value = decoder.tilecol
        tilerow_value = decoder.tilerow
        time_value = decoder.time

        # 2. Store the retrieved textures in the MapCache:
        mapcache_c = mapcache.Connection()
        # FIXXME: get from content object!
        try:
            # filename = 'products/vrvis_demo/Reflectivity_2013137113720_0000.png'
            filename = '/var/ngeob_autotest/data/test_data/test-tile.png'
            texture = open(filename, 'r')
        except:
            print '[MeshCache] file: "' + filename + '" not readable'
        # texture = open('/var/ngeob_autotest/data/reference_test_data/ASA_WS__0P_20100722_101601.jpg', 'r')
        # print 'str size:   ' + str(len(texture.read()))
        # texture.seek(0)
        #print texture

        # FIXXME: use decoder.time!
        # time = '2012-05-17T10:50:00Z/2013-05-17T11:00:00Z'
        time = ''
        # FIXXME: use decoder.layer
        layer = 'TEST_OSM'
        mapcache_c.handle(layer, 'WGS84', time, decoder.tilecol, decoder.tilerow, decoder.tilelevel, texture)

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
        # 1. Get the glTF content from the MeshFactory:
        content = self.get_tile_content_from_factory(decoder)

        # # 2. Store the retrieved textures in the MapCache:
        # mapcache_c = mapcache.Connection()
        # # FIXXME: get from content object!
        # # texture = open('products/vrvis_demo/Reflectivity_2013137113720_0000.png', 'r')
        # texture = open('/var/ngeob_autotest/data/reference_test_data/ASA_WS__0P_20100722_101601.jpg', 'r')
        # print texture

        # print 'vor texture.read()'
        # blob = texture.read();
        # print blob
        # print 'nach texture.read()'

        # # FIXXME: use decoder.time!
        # time = '2013-05-01T13:00:00Z/2013-05-18T15:30:00Z'
        # mapcache_c.handle(decoder.layer, 'WGS84', time, decoder.tilecol, decoder.tilerow, decoder.tilelevel, texture)

        # 3. Rewrite .json to link to the WMTS url of the texture:
        # FIXXME!

        # 4. Create the entry for the glTF content in the MeshCache database:
        # Maybe use File.storage: https://docs.djangoproject.com/en/dev/topics/files/
        tilerow = models.TileRow.objects.create(tilecol=tilecol, value=tilerow_value, content_file=content)

        return tilerow

    def get_tile_content_from_factory(self, decoder):
        layer_value = decoder.layer
        tilelevel_value = decoder.tilelevel
        tilecol_value = decoder.tilecol
        tilerow_value = decoder.tilerow
        time_value = decoder.time

        bbox_str = self.convert_tile_params_to_scene_bbox_string(tilelevel_value, tilecol_value, tilerow_value)
        
        # FIXXME: after a refactoring of gettyle.py into at least a separated MeshCache class the baseurl should be a parameter of this class!
        baseurl = 'http://localhost:8000/ows?service=W3DS&request=GetScene&version=1.0.0&crs=EPSG:4326&format=model/gltf'
        url = '{0}&layer={1}&boundingBox={2}&time={3}'.format(baseurl, layer_value, bbox_str, time_value)

        response = urllib2.urlopen(url)
        data = response.read()
        response.close()

        return data

    def convert_tile_params_to_scene_bbox_string(self, tilelevel, tilecol, tilerow):
        # NOTE: This setting has to be adapted to the grid schema the web-client is using!
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