#-------------------------------------------------------------------------------
#
# Project: V-MANIP Server <http://v-manip.eox.at>
# Authors: Martin Hecher <martin.hecher@fraunhofer.at>
#          Daniel Santillan <daniel.santillan@eox.at>
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


from eoxserver.core import Component, implements
from eoxserver.services.ows.interfaces import (
    ServiceHandlerInterface, GetServiceHandlerInterface
)
from eoxserver.core.decoders import kvp
from vmanip_server.mesh_cache.mesh_cache import MeshCache
import logging


logger = logging.getLogger(__name__)


class W3DSGetTileKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layer = kvp.Parameter()
    time = kvp.Parameter()
    tilelevel = kvp.Parameter(type=int)
    tilerow = kvp.Parameter(type=int)
    tilecol = kvp.Parameter(type=int)


class W3DSGetTileHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    service = "W3DS"
    versions = ["1.0", "1.0.0", "0.4.0"]
    request = "GetTile"

    def handle(self, request):
        decoder = W3DSGetTileKVPDecoder(request.GET)

        layer = decoder.layer
        grid = decoder.crs
        level = decoder.tilelevel
        col = decoder.tilecol
        row = decoder.tilerow
        time = decoder.time

        print 'level: ' + str(level)

        # magic seeding request:
        if level == 9999:
            logger.debug('[W3DSGetTileHandler::handle] started seeding for levels %s-%s:' % (col, row))
            self.seed(layer, grid, range(col, row), time)
            return ('{ "status:" "finished seeding of levels %s-%s" }' % (col, row), 'application/json')

        logger.debug('[W3DSGetTileHandler::handle] %s / %s / %s / %s / %s / %s' % (layer, grid, level, col, row, time))

        mesh_cache = MeshCache()
        tile_geo = mesh_cache.lookup(layer, grid, level, col, row, time)

        # FIXXME: debugging only!
        # tile_geo = False

        if not tile_geo:
            print 'No tile geometry available, requesting from source (MeshFactory) ...'
            tile_geo = mesh_cache.request_and_store(layer, grid, level, col, row, time)

            # print 'TILE_GEO: ', tile_geo

            if not tile_geo:
                raise Exception('Could not request data from source (MeshFactory)')

        logger.debug('[W3DSGetTileHandler::handle] returning tile_geo\n%s:' % (tile_geo,))

        return (tile_geo, 'application/json')

    def seed(self, layer, grid, level_range, time):
        level_0_num_tiles_y = 2  # rows
        level_0_num_tiles_x = 4  # cols

        mesh_cache = MeshCache()

        for level in level_range:
            for row in range(0, pow(level_0_num_tiles_y, level)):
                for col in range(0, pow(level_0_num_tiles_x, level)):
                    logger.debug('[W3DSGetTileHandler::seed] processing %s / %s / %s / %s / %s/ %s' % (layer, grid, level, col, row, time))
                    if not mesh_cache.lookup(layer, grid, level, col, row, time):
                        mesh_cache.request_and_store(layer, grid, level, col, row, time)
