


from eoxserver.core import Component, implements
from eoxserver.services.ows.interfaces import ExceptionHandlerInterface



class W3DSExceptionHandler(Component):
    implements(ExceptionHandlerInterface)

    service = "W3DS"
    versions = ["1.0", "1.0.0"]
    request = None

    def handle_exception(self, request, exception):


        return response
