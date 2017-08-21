#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Module: KodiHelper
# Created on: 13.01.2017

import xbmcgui
import xbmc
import json
import os
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

    def get_setting(self, key):
        return self.get_addon().getSetting(key)

    def set_setting(self, key, value):
        """Public interface for the addons setSetting method

        Returns
        -------
        bool
            Setting could be set or not
        """
        return self.get_addon().setSetting(key, value)
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
            'username': self.get_addon().getSetting('username'),
            'password': self.get_addon().getSetting('password')
        }
    def set_credentials(self,username,password):
        self.set_setting("username", username)
        self.set_setting("password", password)
    def log(self, msg, level=xbmc.LOGNOTICE):
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
        xbmc.log('[%s] %s' % (self.plugin, msg.__str__()), level)

    def show_message(self, message, title, level=xbmcgui.NOTIFICATION_ERROR):
        dialog = xbmcgui.Dialog()
        dialog.notification(title, message, level, 3000)
        return True
    
    def get_local_string(self, string_id):
        """Returns the localized version of a string

        Parameters
        ----------
        string_id : :obj:`int`
            ID of the string that shoudl be fetched

        Returns
        -------
        :obj:`str`
            Requested string or empty string
        """
        src = xbmc if string_id < 30000 else self.get_addon()
        locString = src.getLocalizedString(string_id)
        if isinstance(locString, unicode):
            locString = locString.encode('utf-8')
        return locString

    def get_inputstream_addon(self):
        """Checks if the inputstream addon is installed & enabled.
           Returns the type of the inputstream addon used or None if not found

        Returns
        -------
        :obj:`str` or None
            Inputstream addon or None
        """
        addon_type = 'inputstream.adaptive'
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': addon_type,
                'properties': ['enabled']
            }
        }
        response = xbmc.executeJSONRPC(json.dumps(payload))
        data = json.loads(response)
        if not 'error' in data.keys():
            if data['result']['addon']['enabled'] == True:
                return addon_type
        return None
    
    def open_settings(self):
        self.get_addon().openSettings()
        return
    