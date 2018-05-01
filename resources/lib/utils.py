import urlparse
import urllib
import urllib2
import json
import threading
import SocketServer
import socket
import xbmc
import xbmcaddon
try:
    import cPickle as pickle
except ImportError:
    import pickle
from resources.lib import Logger

def get_bool(text):
    text = str(text).lower()
    return text == "true"

def get_setting(key, defaultValue=None):
    value = xbmcaddon.Addon().getSetting(key)
    if (value == None or len(value) == 0):
        if defaultValue!=None:
            set_setting(key, defaultValue)
        return defaultValue
    elif value == "true" or value == "false":
        return get_bool(value)
    return value

def open_settings():
    xbmcaddon.Addon().openSettings()
    return

def set_setting(key, value):
    xbmcaddon.Addon().setSetting(key, value)

def get_service_url():
    return 'http://127.0.0.1:' + str(get_setting('timvision_service_port')+"/")

def call_service(method, params={}, try_time=1):
    try:
        params.update({"method":method})
        url_values = urllib.urlencode(params)
        full_url = get_service_url() + '?' + url_values
        Logger.log_write(full_url, Logger.LOG_API)
        data = urllib2.urlopen(full_url).read()
        parsed_json = json.loads(data)
        result = parsed_json.get('result', None)
        return result
    except urllib2.URLError as error:
        Logger.log_write("webserver error: %s" % (str(error.reason)), Logger.LOG_API)
        if try_time == 5:
            Logger.log_write("TryTime limit reach. Returning None", Logger.LOG_API)
            return None
        start_webserver()
        call_service(method, params, try_time+1)

def get_user_agent():
    return 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0'

def get_parameters_dict_from_url(parameters):
    return dict(urlparse.parse_qsl(parameters[1:]))

def url_join(base_url='', other=''):
    return base_url + ('/' if not base_url.endswith('/') and not other.startswith('/') else '') + other

def get_addon(addon_id):
    is_enabled = False
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Addons.GetAddonDetails',
        'params': {
            'addonid': addon_id,
            'properties': ['enabled']
        }
    }
    response = xbmc.executeJSONRPC(json.dumps(payload))
    data = json.loads(response)
    if 'error' not in data.keys():
        if isinstance(data.get('result'), dict):
            if isinstance(data.get('result').get('addon'), dict):
                is_enabled = data.get('result').get('addon').get('enabled')
        return (addon_id, is_enabled)
    return (None, is_enabled)

def get_kodi_version():
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Application.GetProperties',
        'params': [["version"]]
    }
    response = xbmc.executeJSONRPC(json.dumps(payload))
    data = json.loads(response)
    major = int(data["result"]["version"]["major"])
    minor = int(data["result"]["version"]["minor"])
    return major, minor

def get_json_rpc_call(method_name, parameters=None):
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': method_name,
        'params': [parameters] if parameters!=None else []
    }
    response = xbmc.executeJSONRPC(json.dumps(payload))
    return json.loads(response)

def list_to_string(mylist, separator=', '):
    if mylist is None:
        return ""
    content_list = ""
    for item in mylist:
        content_list += ("%s%s" % (separator if len(content_list) > 0 else '', item.encode('utf-8')))
    return content_list

def string_to_list(mystring, separator):
    if mystring is None:
        return []
    return mystring.split(separator)

def get_timestring_from_seconds(total_seconds):
    seconds = int(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)

def get_data_folder():
    kodi_profile_dir = xbmcaddon.Addon().getAddonInfo("profile")
    return xbmc.translatePath(kodi_profile_dir)

def save_pickle(item, pickle_file):
    folder = get_data_folder()
    path = url_join(folder, pickle_file)
    with open(path, "w") as file_stream:
        file_stream.truncate()
        pickle.dump(item, file_stream)
    file_stream.close()

def load_pickle(pickle_file, default=None):
    folder = get_data_folder()
    path = url_join(folder, pickle_file)
    try:
        content = default
        with open(path, "r") as file_stream:
            content = pickle.load(file_stream)
        file_stream.close()
        return content
    except:
        Logger.kodi_log("Error while loading %s" % (pickle_file))
        return default

def select_unused_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    _, port = sock.getsockname()
    sock.close()
    return port

def start_webserver():
    Logger.kodi_log("Starting TIMVISION addon")
    
    # pick & store a port for the internal TimVision HTTP proxy service
    tv_port = select_unused_port()
    set_setting('timvision_service_port', str(tv_port))

    # server defaults
    SocketServer.TCPServer.allow_reuse_address = True

    # configure the TimVision Data Server
    from resources.lib.TimVisionHttpRequestHandler import TimVisionHttpRequestHandler
    tv_server = SocketServer.TCPServer(('127.0.0.1', tv_port), TimVisionHttpRequestHandler)
    tv_server.server_activate()
    tv_server.timeout = 1

    tv_thread = threading.Thread(target=tv_server.serve_forever)
    tv_thread.daemon = True
    tv_thread.start()

    return tv_server

def get_local_string(string_id):
    locString = xbmcaddon.Addon().getLocalizedString(string_id)
    if isinstance(locString, unicode):
        locString = locString.encode('utf-8')
    return locString
