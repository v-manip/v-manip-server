#-------------------------------------------------------------------------------
#
# Project: V-MANIP Server <http://v-manip.eox.at>
# Authors: Martin Hecher <martin.hecher@fraunhofer.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 Fraunhofer Austria GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------


import json
import datetime
import logging


logger = logging.getLogger(__name__)


class TimeSlider(object):
    '''
    This class takes a gltf-json file and a timespan and clips the meshes
    stored in the file to only show the meshes within the timespan. For that
    to work the meshes in the file have to be named after with the following
    schema: ('$$$' is a delimiter that separates name and timespan)
    NAME$$$TIMESPAN, e.g.
    'mynodename$$$2013-05-17T11:21:04+00:00/2013-05-17T11:23:40+00:00'

    If an invalid input is detected the original gltf data is returned.
    '''

    def trim(self, gltf_string, timespan, delimiter):
        tmp = timespan.split('/')

        if len(tmp) != 2:
            logger.error('[TimeSlider::trim] Skipping invalid time format: ' + str(timespan))
            return gltf_string

        try:
            timespan_start = datetime.datetime.strptime(tmp[0], '%Y-%m-%dT%H:%M:%S.%fZ')
            timespan_end = datetime.datetime.strptime(tmp[1], '%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            logger.error('[TimeSlider::trim] strptime exception! timespan in: %s' % (timespan,))
            return gltf_string

        gltf_data = json.loads(gltf_string)
        valid_meshes = []

        for mesh in gltf_data['meshes']:
            mesh_timespan = self._getTimespan(gltf_data['meshes'][mesh], delimiter)

            if mesh_timespan:
                # print('mesh_timespan: start: ' + str(mesh_timespan[0]) + ' / end: ' + str(mesh_timespan[1]))
                # print('timespan_start      : ' + str(timespan_start) + '   / end: ' + str(timespan_end))

                if (mesh_timespan[0] > timespan_start and mesh_timespan[0] <= timespan_end) or (mesh_timespan[1] > timespan_start and mesh_timespan[1] <= timespan_end):
                    # print('added mesh')
                    valid_meshes.append(mesh)
                # else:
                #     print('no mesh added')

        print('#valid_meshes: ' + str(len(valid_meshes)))

        # FIXXME: this is hardcoded to 'node0' at the moment, as we know which geometry/names we are creating.
        # It would be reasonable to have this generalized!
        gltf_data['nodes']['node0']['meshes'] = valid_meshes

        return json.dumps(gltf_data)

    def _getTimespan(self, mesh, delimiter):
        timespan = None

        name = mesh['name']

        # example name: 5fc4421e277741fe937156cf99a88b12_Reflectivity_2013137095827_0019_proc-2013-05-17T11:21:04+00:00_2013-05-17T11:23:40+00:00
        idx = name.find('-')

        if idx != -1:
            idx += 1
            timespan = name[idx:]

        if timespan:
            tmp = timespan.split('_')
            try:
                # NOTE: strips off milliseconds!
                res = (datetime.datetime.strptime(tmp[0].split('+')[0], '%Y-%m-%dT%H:%M:%S'), datetime.datetime.strptime(tmp[1].split('+')[0], '%Y-%m-%dT%H:%M:%S'))
            except:
                print('[TimeSlider::_getTimespan] strptime exception! tmp[0]: %s + / tmp[1]: %s' % (tmp[0], tmp[1]))

            return res

        return None
