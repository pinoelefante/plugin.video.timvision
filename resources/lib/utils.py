import os
import xbmcaddon

def get_bool(text):
    text = text.lower()
    return text=="true"

def log_on_desktop_file(msg, filename="timvision.log"):
    if not get_bool(get_setting("abilita_log_desktop")):
        return
    if(msg != None):
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        desktop = os.path.join(os.environ["HOMEPATH"], "Desktop")
        filepath = os.path.join(desktop, filename)
        f = open(filepath, "a")
        f.writelines(msg + "\n")
        f.close()

def get_setting(key):
    return xbmcaddon.Addon().getSetting(key)