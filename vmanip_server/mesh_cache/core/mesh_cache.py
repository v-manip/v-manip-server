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


from vmanip_server.mesh_cache.datasource.mesh_factory_client import MeshFactoryClient
from vmanip_server.mesh_cache.backend.mapcache_sqlite import MapCacheSQLite
import os
import logging


logger = logging.getLogger(__name__)


class MeshCache(object):
    def __init__(self):
        # FIXXME: get parameters from config!
        self.cache = MapCacheSQLite('/var/www/cache')
        self.source = MeshFactoryClient('http://localhost/browse/ows')
        self.gltf_folder = '/var/www/cache/gltf/'

        try:
            if not os.path.exists(self.gltf_folder):
                print '[MeshCache] creating gltf folder in: ' + str(self.gltf_folder)
                os.makedirs(self.gltf_folder)
        except:
            # FIXXME: not so beautiful, but it catches an exception when multiple requests
            # want to create the folder simultaneously
            pass

    def lookup(self, layer, grid, level, col, row, time):
        logger.info('[MeshCache::lookup] Tile parameters: %s / %s / %s / %s'
                    % (layer, level, col, row))

        tile_geo = self.cache.lookup(layer, grid, level, col, row, time)

        return tile_geo

    def request_and_store(self, layer, grid, level, col, row, time):
        logger.info('[MeshCache::request_and_store] Tile parameters: %s / %s / %s / %s'
                    % (layer, level, col, row))

        files = self.source.request_files(layer, grid, level, col, row, time)
        tilesets = self._convert_files_to_tilesets(files)
        tile_geo = self.cache.store(layer, grid, level, col, row, time, tilesets)

        # FIXXME: Currently dependent glTF files are simply written to a folder on the server. The
        # .json file links to the published endpoint of this folder. In future the dependent files
        # will also be stored in the sqlite-db!
        for file in files:
            target = open(self.gltf_folder + file['name'], 'w')

            # target.write(file['buffer'].replace('"path": "', '"path": "http://localhost:3080/gltf/'))
            target.write(file['buffer'])
            # logger.info('Wrote to: ' + self.gltf_folder + file['name'])

        return tile_geo

    def _convert_files_to_tilesets(self, files):
        file_json = None

        for item in files:
            if item['name'].endswith('.json'):
                file_json = item['buffer']

        tileset_wmts = {}
        tileset_wmts['protocol'] = 'WMTS'
        tileset_wmts['data'] = 'test'

        tileset_w3ds = {}
        tileset_w3ds['protocol'] = 'W3DS'
        tileset_w3ds['json'] = file_json
        tileset_w3ds['bin'] = ''
        tileset_w3ds['vert'] = ''
        tileset_w3ds['frag'] = ''

        tilesets = []
        tilesets.append(tileset_wmts)
        tilesets.append(tileset_w3ds)

        logger.info('[MeshCache::_convert_files_to_tilesets] converted files to tilesets')

        return tilesets
