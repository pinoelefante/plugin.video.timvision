import urlparse, urllib, urllib2
import json
from resources.lib import Logger
import xbmc
import xbmcaddon

def get_bool(text):
    text = text.lower()
    return text=="true"

def get_setting(key):
    value = xbmcaddon.Addon().getSetting(key)
    if value=="true" or value=="false":
        return get_bool(value)
    return value

def open_settings():
    xbmcaddon.Addon().openSettings()
    return

def set_setting(key,value):
    xbmcaddon.Addon().setSetting(key, value)

def get_service_url():
    return 'http://127.0.0.1:' + str(get_setting('timvision_service_port')+"/")

def call_service(method,params={}):
    params.update({"method":method})
    url_values = urllib.urlencode(params)
    full_url = get_service_url() + '?' + url_values
    if get_setting("log_all_apicalls"):
        Logger.kodi_log(full_url)
    data = urllib2.urlopen(full_url).read()
    parsed_json = json.loads(data)
    result = parsed_json.get('result', None)
    return result

def get_user_agent():
    return 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0'

def get_parameters_dict_from_url(parameters):
    return dict(urlparse.parse_qsl(parameters[1:]))

def url_join(baseUrl='', other=''):
    return baseUrl + ('/' if not baseUrl.endswith('/') and not other.startswith('/') else '') + other

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