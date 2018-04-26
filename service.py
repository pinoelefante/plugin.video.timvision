import xbmc
from resources.lib import utils, TimVisionLibrary

class TimVisionService(object):
    def __init__(self):
        self.timvision_server = utils.start_webserver()
        self.library = TimVisionLibrary.TimVisionLibrary()

    def run(self):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            self.library.update()
            if monitor.waitForAbort(5):
                self.shutdown()
                break
    
    def shutdown(self):
        self.timvision_server.shutdown()
        self.timvision_server.server_close()
        self.timvision_server.socket.close()

if __name__ == "__main__":
    utils.set_setting("kodi_version_alert_shown", "false")
    TimVisionService().run()