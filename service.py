import xbmc
from resources.lib import utils

utils.set_setting("kodi_version_alert_shown", "false")
TV_SERVER = utils.start_webserver()

if __name__ == "__main__":
    MONITOR = xbmc.Monitor()

    # kill the services if kodi monitor tells us to
    while not MONITOR.abortRequested():
        if MONITOR.waitForAbort(5):
            TV_SERVER.shutdown()
            break

    # webserver shutdown sequence
    TV_SERVER.server_close()
    TV_SERVER.socket.close()
    TV_SERVER.shutdown()
