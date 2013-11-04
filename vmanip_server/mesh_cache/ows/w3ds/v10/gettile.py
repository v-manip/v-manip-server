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


# handler definition


class W3DSGetTileHandler(Component):
    implements(ServiceHandlerInterface)
    implements(GetServiceHandlerInterface)

    service = "W3DS"
    versions = ["1.0"]
    request = "GetTile"

    def handle(self, request):

        return """Response for GetTile Request"""

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


class W3DSGetTileKVPDecoder(kvp.Decoder):
    crs = kvp.Parameter()
    layer = kvp.Parameter()
    tilelevel = kvp.Parameter(type=int)
    tilerow = kvp.Parameter(type=int)
    tilecol = kvp.Parameter(type=int)
    '''
