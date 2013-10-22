# copyright notice



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
        # request is a Django HTTPRequest object

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

