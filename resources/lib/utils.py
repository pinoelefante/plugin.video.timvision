import os
import platform
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
        desktop = get_desktop_directory()
        filepath = os.path.join(desktop, filename)
        f = open(filepath, "a")
        f.writelines(msg + "\n")
        f.close()

def get_setting(key):
    return xbmcaddon.Addon().getSetting(key)

def get_desktop_directory():
    os_name = platform.system()
    if os_name == "Windows":
        return os.path.join(os.environ["HOMEPATH"] , "Desktop")
    if os_name == "Linux":
        return os.environ["HOME"]
    if os_name == "Darwin":
        return os.environ["HOME"]
    return ""