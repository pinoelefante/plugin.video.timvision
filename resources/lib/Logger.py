import os
import platform
import time
import xbmc

LOG_API = "api"
LOG_TIMVISION = "timvision"
LOG_PLAYER = "player"
LOG_WIDEVINE = "widevine"

def log_write(msg, mode):
    from resources.lib import utils

    if not utils.get_setting("debug_enable"):
        return

    if mode == LOG_API and not utils.get_setting("log_all_apicalls"):
        return
    if mode == LOG_TIMVISION and not utils.get_setting("logd_timvision"):
        return
    if mode == LOG_PLAYER and not utils.get_setting("logd_player"):
        return
    if mode == LOG_WIDEVINE and not utils.get_setting("logd_widevine"):
        return

    if msg != None:
        if not isinstance(msg, str):
            msg = msg.encode('utf-8')
        message = "[%s] - %s" % (mode, msg)
        kodi_log(message)

def kodi_log(msg, level=xbmc.LOGINFO):
    """
        Adds a log entry to the Kodi log
    """
    if not isinstance(msg, str):
        msg = msg.encode('utf-8')
    xbmc.log('[%s] %s' % ("TIMVISION", msg.__str__()), level)
