import threading
import SocketServer
import socket
from xbmc import Monitor
from resources.lib.KodiHelper import KodiHelper
from resources.lib.TimVisionHttpRequestHandler import TimVisionHttpRequestHandler

# helper function to select an unused port on the host machine
def select_unused_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    addr, port = sock.getsockname()
    sock.close()
    return port

kodi_helper = KodiHelper()

# pick & store a port for the internal TimVision HTTP proxy service
tv_port = select_unused_port()
kodi_helper.set_setting('timvision_service_port', str(tv_port))

# server defaults
SocketServer.TCPServer.allow_reuse_address = True

# configure the TimVision Data Server
nd_server = SocketServer.TCPServer(('127.0.0.1', tv_port), TimVisionHttpRequestHandler)
nd_server.server_activate()
nd_server.timeout = 1

if __name__ == '__main__':
    monitor = Monitor()

    # start thread for TimVision HTTP service
    nd_thread = threading.Thread(target=nd_server.serve_forever)
    nd_thread.daemon = True
    nd_thread.start()

    # kill the services if kodi monitor tells us to
    while not monitor.abortRequested():
        if monitor.waitForAbort(5):
            nd_server.shutdown()
            break

    # Netflix service shutdown sequence
    nd_server.server_close()
    nd_server.socket.close()
    nd_server.shutdown()
