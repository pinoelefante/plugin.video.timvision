import os
import platform
import urllib, urllib2
import json
import xbmc
import xbmcaddon

LOG_TIMVISION_FILE = "timvision.log"
LOG_PLAYER_FILE = "player.log"
LOG_WIDEVINE_FILE = "widevine.log"

def get_bool(text):
    text = text.lower()
    return text=="true"

def log_on_desktop_file(msg, filename=LOG_TIMVISION_FILE):
    if not get_setting("abilita_log_desktop"):
        return

    if filename == LOG_TIMVISION_FILE and not get_setting("logd_timvision"):
        return
    if filename == LOG_PLAYER_FILE and not get_setting("logd_player"):
        return
    if filename == LOG_WIDEVINE_FILE and not get_setting("logd_widevine"):
        return

    if(msg != None):
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        desktop = get_desktop_directory()
        filepath = os.path.join(desktop, filename)
        f = open(filepath, "a")
        f.writelines(msg + "\n")
        f.close()

def kodi_log(msg, level=xbmc.LOGNOTICE):
    """Adds a log entry to the Kodi log

    Parameters
        ----------
        msg : :obj:`str`
        Entry that should be turned into a list item

        level : :obj:`int`
            Kodi log level
    """
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log('[%s] %s' % ("TIMVISION", msg.__str__()), level)

def get_setting(key):
    value = xbmcaddon.Addon().getSetting(key)
    if value=="true" or value=="false":
        return get_bool(value)
    return value

def set_setting(key,value):
    xbmcaddon.Addon().setSetting(key, value)

def get_desktop_directory():
    os_name = platform.system()
    if os_name == "Windows":
        return os.path.join(os.environ["HOMEPATH"] , "Desktop")
    if os_name == "Linux":
        return os.environ["HOME"]
    if os_name == "Darwin":
        return os.environ["HOME"]
    return ""

def get_timvision_service_url():
    return 'http://127.0.0.1:' + str(get_setting('timvision_service_port'))

def call_timvision_service(params):
    url_values = urllib.urlencode(params)
    url = get_timvision_service_url()
    full_url = url + '?' + url_values
    if get_setting("log_all_apicalls"):
        kodi_log(full_url)
    data = urllib2.urlopen(full_url).read()
    parsed_json = json.loads(data)
    result = parsed_json.get('result', None)
    return result

def get_user_agent():
    return 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0'