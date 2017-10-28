import os
import platform
import xbmc

LOG_TIMVISION_FILE = "timvision.log"
LOG_PLAYER_FILE = "player.log"
LOG_WIDEVINE_FILE = "widevine.log"

def get_desktop_directory():
    os_name = platform.system()
    if os_name == "Windows":
        return os.path.join(os.environ["HOMEPATH"], "Desktop")
    if os_name == "Linux":
        return os.environ["HOME"]
    if os_name == "Darwin":
        return os.environ["HOME"]
    return ""

def log_on_desktop_file(msg, filename=LOG_TIMVISION_FILE):
    from resources.lib import utils

    if not utils.get_setting("abilita_log_desktop"):
        return

    if filename == LOG_TIMVISION_FILE and not utils.get_setting("logd_timvision"):
        return
    if filename == LOG_PLAYER_FILE and not utils.get_setting("logd_player"):
        return
    if filename == LOG_WIDEVINE_FILE and not utils.get_setting("logd_widevine"):
        return

    if msg != None:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        desktop = get_desktop_directory()
        filepath = os.path.join(desktop, filename)
        f = open(filepath, "a")
        f.writelines(msg + "\n")
        f.close()

def kodi_log(msg, level=xbmc.LOGNOTICE):
    """
        Adds a log entry to the Kodi log
    """
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log('[%s] %s' % ("TIMVISION", msg.__str__()), level)
