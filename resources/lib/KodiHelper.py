import xbmcgui
import xbmc
import json
import os
from resources.lib import utils
from xbmcaddon import Addon


class KodiHelper:
    """Consumes all the configuration data from Kodi as well as turns data into lists of folders and videos"""

    def __init__(self, plugin_handle=None, base_url=None):
        """Fetches all needed info from Kodi & configures the baseline of the plugin

        Parameters
        ----------
        plugin_handle : :obj:`int`
            Plugin handle

        base_url : :obj:`str`
            Plugin base url
        """
        addon = self.get_addon()
        self.plugin_handle = plugin_handle
        self.base_url = base_url
        self.plugin = addon.getAddonInfo('name')
        self.version = addon.getAddonInfo('version')
        self.base_data_path = xbmc.translatePath(addon.getAddonInfo('profile'))
        self.home_path = xbmc.translatePath('special://home')
        self.plugin_path = addon.getAddonInfo('path')
        self.cookie_path = self.base_data_path + 'COOKIE'
        self.data_path = self.base_data_path + 'DATA'
        self.default_fanart = addon.getAddonInfo('fanart')

    def get_addon(self):
        """Returns a fresh addon instance"""
        return Addon()

    def show_text_field(self, label=""):
        dlg = xbmcgui.Dialog()
        return dlg.input(label, type=xbmcgui.INPUT_ALPHANUM)

    def show_password_field(self):
        dlg = xbmcgui.Dialog()
        return dlg.input("Password", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)

    def get_credentials(self):
        """Returns the users stored credentials

        Returns
        -------
        :obj:`dict` of :obj:`str`
            The users stored account data
        """
        return {
            'username': utils.get_setting('username'),
            'password': utils.get_setting('password')
        }

    def set_credentials(self,username,password):
        utils.set_setting("username", username)
        utils.set_setting("password", password)

    def show_message(self, message, title, level=xbmcgui.NOTIFICATION_ERROR):
        dialog = xbmcgui.Dialog()
        dialog.notification(title, message, level, 3000)
        return True

    def show_dialog(self,message,title):
        dialog = xbmcgui.Dialog()
        dialog.ok(title,message)
        return True
    
    def get_inputstream_addon(self):
        """Checks if the inputstream addon is installed & enabled.
           Returns the type of the inputstream addon used and if it's enabled,
           or None if not found.
        Returns
        -------
        :obj:`tuple` of obj:`str` and bool, or None
            Inputstream addon and if it's enabled, or None
        """
        addon_id = 'inputstream.adaptive'
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
    
    def open_settings(self):
        self.get_addon().openSettings()
        return
    