try:
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
except:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from urlparse import urlparse, parse_qs

import json
from types import FunctionType

from resources.lib.TimVisionAPI import TimVisionSession
from resources.lib.TimVisionHttpSubRessourceHandler import TimVisionHttpSubRessourceHandler

TIMVISION = TimVisionSession()
METHODS = [x for x, y in TimVisionHttpSubRessourceHandler.__dict__.items() if isinstance(y, FunctionType)]
SUB_HANDLER = TimVisionHttpSubRessourceHandler(timvision_session=TIMVISION)

class TimVisionHttpRequestHandler(BaseHTTPRequestHandler):
    """ Represents the callable internal server that dispatches requests to TimVision"""

    def do_GET(self):
        """GET request handler (we only need this, as we only do GET requests internally)"""
        url = urlparse(self.path)
        params = parse_qs(url.query)
        method = params.get('method', [None])[0]

        # not method given
        if method is None:
            self.send_error(500, 'No method declared')
            return

        # no existing method given
        if method not in METHODS:
            self.send_error(404, 'Method ' + str(method) + ' not found. Available methods: ' + str(METHODS))
            return
        # call method & get the result
        getattr(SUB_HANDLER, "time_log")()
        result = getattr(SUB_HANDLER, method)(params)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'method': method, 'result': result}).encode())
        return

    def do_POST(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)
        method = params.get("action")[0]

        # not method given
        if method is None:
            self.send_error(500, 'No method declared')
            return

        # no existing method given
        if method not in METHODS:
            self.send_error(404, 'Method ' + str(method) + ' not found. Available methods: ' + str(METHODS))
            return

        rawdata = self.rfile.read(int(self.headers.getheader('Content-Length')))
        # call method & get the result
        getattr(SUB_HANDLER, "time_log")()
        result = getattr(SUB_HANDLER, method)(params, rawdata)

        self.send_response(200 if result != None else 500)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(result.encode() if result != None else "".encode())
        return

    def log_message(self, format, *args):
        """Disable the BaseHTTPServer Log"""
        return
