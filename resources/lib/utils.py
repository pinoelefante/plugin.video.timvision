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
    text = text.lower()
    return text == "true"

def get_setting(key):
    value = xbmcaddon.Addon().getSetting(key)
    if value == "true" or value == "false":
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
        if get_setting("log_all_apicalls"):
            Logger.kodi_log(full_url)
        data = urllib2.urlopen(full_url).read()
        parsed_json = json.loads(data)
        result = parsed_json.get('result', None)
        return result
    except urllib2.URLError as error:
        Logger.kodi_log("webserver error: %s" % (str(error.reason)))
        if try_time == 5:
            Logger.kodi_log("TryTime limit reach. Returning None")
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
    return int(data["result"]["version"]["major"]), int(data["result"]["version"]["minor"])

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
    addr, port = sock.getsockname()
    sock.close()
    return port

def start_webserver():
    Logger.kodi_log("Starting webserver")

    # pick & store a port for the internal TimVision HTTP proxy service
    tv_port = select_unused_port()
    set_setting('timvision_service_port', str(tv_port))

    # server defaults
    SocketServer.TCPServer.allow_reuse_address = True

    # configure the TimVision Data Server
    from resources.lib.TimVisionHttpRequestHandler import TimVisionHttpRequestHandler
    nd_server = SocketServer.TCPServer(('127.0.0.1', tv_port), TimVisionHttpRequestHandler)
    nd_server.server_activate()
    nd_server.timeout = 1

    ws_thread = threading.Thread(target=__start_webserver, args=([nd_server]))
    ws_thread.daemon = True
    ws_thread.start()

def __start_webserver(nd_server):
    monitor = xbmc.Monitor()

    # start thread for TimVision HTTP service
    nd_thread = threading.Thread(target=nd_server.serve_forever)
    nd_thread.daemon = True
    nd_thread.start()

    # kill the services if kodi monitor tells us to
    while not monitor.abortRequested():
        if monitor.waitForAbort(5):
            nd_server.shutdown()
            break

    # webserver shutdown sequence
    nd_server.server_close()
    nd_server.socket.close()
    nd_server.shutdown()
