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
from eoxserver.core.util import multiparttools as mp
import urllib2
import logging


logger = logging.getLogger(__name__)


class MeshFactoryClient(object):
    def __init__(self, host):
        self.host = host

    def request_files(self, layer, grid, level, col, row, time):
        bbox = self._convert_tile_params_to_scene_bbox(level, col, row)

        # from the W3DS standard draft:
        # "The value of the BoundingBox parameter is a list of comma-separated real
        # numbers in the form 'minx,miny,maxx,maxy'."
        bbox_str = '%s,%s,%s,%s' % (bbox['west'], bbox['south'], bbox['east'], bbox['north'])

        # NOTE: The MeshFactory does not take into account the timespan, it
        # delivers all data (timewise) for a given tile.
        #time = '2013-05-17T11:10:34.000Z/2013-05-17T11:26:18.000Z'

        # FIXXME: those parameters should be configurable!
        baseurl = self.host + '?service=W3DS&request=GetScene&version=1.0.0&crs=WGS84&format=model/gltf'
        url = '{0}&layer={1}&boundingBox={2}&time={3}'.format(baseurl, layer, bbox_str, time)

        # logger.debug('URL: %s' % (url,))

        response = urllib2.urlopen(url)
        files = self._extract_files_from_response(response)
        response.close()

        return files

    # TODO: do code cleanup!
    def _extract_files_from_response(self, response):
        files = []

        ct = None
        boundary = None
        fn = None

        for header in response.info().headers:
            if header.startswith('Content-Type'):
                ct = header.split(': ')[1].strip()
            if header.startswith('Content-Disposition'):
                fn = header.split('; ')[1].split('=')[1]
                fn = fn.split('"')[1]  # A 'header' line is terminated with a '\r'. This split takes care of that.
                fn = fn.strip()  # Just to be sure...

        if not ct.startswith('multipart'):
            raw_data = response.read()

            file_info = {}
            file_info['name'] = fn
            file_info['buffer'] = raw_data
            files.append(file_info)
            return files
        else:
            boundary = ct.split('; ')[1].split('=')[1]

        data = response.read()

        # print 'BOUNDARY: ', boundary
        raw_data = mp.mpUnpack(data, boundary)

        # print('#files in response: ' + str(len(raw_data)))

        for file_info in raw_data:
            info = file_info[0]
            offset = file_info[1]
            length = file_info[2]

            filename = info['content-disposition'].split(';')[1].split('"')[1]
            end = offset + length
            # print 'end:' + str(end)
            filebuffer = data[offset:end]

            file_info = {}
            file_info['name'] = filename
            file_info['buffer'] = filebuffer
            files.append(file_info)

            # print('filename: ' + filename)

            # print('Offset:' + str(offset))
            # print('Length:' + str(length))

            # print('Buffer: \n\n' + str(buffer))
            # print('\n\n')

        return files

    def _convert_tile_params_to_scene_bbox(self, level, col, row):
        # NOTE: This setting has to be adapted to the tiling schema the web-client
        # is using. We are using those values as level_0 (reflected in the
        # calculation below, where 'level-1' is used), however, other schemas
        # are starting with half of the tiles (1 row, 2 cols) as level_0.
        # FIXXME: those parameters should be configurable!
        level_0_num_tiles_y = 2  # rows
        level_0_num_tiles_x = 4  # cols

        # NOTE: Depending on the tiling schema and the number of level_0 tiles
        # the current division through 'level-1' has to be adapted.
        tile_width = 360 / (level_0_num_tiles_x * pow(2, level-1))
        tile_height = 180 / (level_0_num_tiles_y * pow(2, level-1))

        # print 'tile_width  (level: ' + str(level) + ') = ' + str(tile_width)
        # print 'tile_height (level: ' + str(level) + ') = ' + str(tile_height)

        west = -180 + (col * tile_width)
        east = west + tile_width
        north = 90 - (row * tile_height)
        south = north - tile_height

        return {'west': west, 'south': south, 'east': east, 'north': north}
