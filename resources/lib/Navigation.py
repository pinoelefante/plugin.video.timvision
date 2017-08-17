import json
import urlparse
import urllib
import urllib2
import xbmc
import xbmcgui
import xbmcplugin

from resources.lib import TimVisionAPI

class Navigation:
    def __init__(self, handle, plugin, kodi_helper):
        self.plugin_handle = handle
        self.plugin_dir = plugin
        self.kodi_helper = kodi_helper

    def router(self, parameters):
        params = self.parameters_string_to_dict(parameters)
        params_count = len(params)
        if params_count == 0:
            self.create_home_page()
        else:
            if params.has_key("page"):
                page = params.get("page")
                if page == "RECOMMENDED":
                    self.create_recommended_page()
                if page == TimVisionAPI.RECOM_TOP_VIEW or page == TimVisionAPI.RECOM_MOST_RECENT or page == TimVisionAPI.RECOM_FOR_YOU or page == TimVisionAPI.RECOM_EXPIRING:
                    self.populate_recommended_folder(page)
    
    def parameters_string_to_dict(self, parameters):
        return dict(urlparse.parse_qsl(parameters[1:]))

    def create_home_page(self):
        recomDir = xbmcgui.ListItem(label='Raccomandati')
        xbmcplugin.addDirectoryItem(isFolder=True, handle = self.plugin_handle, listitem = recomDir, url=self.plugin_dir+"?page=RECOMMENDED")
        xbmcplugin.endOfDirectory(handle = self.plugin_handle)

    def create_recommended_page(self):
        top_views = xbmcgui.ListItem(label="Piu' visti")
        most_recents = xbmcgui.ListItem(label="Piu' recenti")
        for_you = xbmcgui.ListItem(label='Consigliati per te')
        expiring = xbmcgui.ListItem(label='In scadenza')
        xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=True, listitem = top_views, url = self.plugin_dir+"?page="+TimVisionAPI.RECOM_TOP_VIEW)
        xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=True, listitem = most_recents, url = self.plugin_dir+"?page="+TimVisionAPI.RECOM_MOST_RECENT)
        xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=True, listitem = for_you, url = self.plugin_dir+"?page="+TimVisionAPI.RECOM_FOR_YOU)
        xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=True, listitem = expiring, url = self.plugin_dir+"?page="+TimVisionAPI.RECOM_EXPIRING)
        xbmcplugin.endOfDirectory(handle = self.plugin_handle)
    
    def create_film_item(self, movie):
        li = xbmcgui.ListItem(label=movie["metadata"]["title"])
        return li

    def populate_recommended_folder(self,page_type):
        items = self.call_timvision_service({"method":"recommended_video", "category":page_type})
        if items is None or not items:
            return

        for movie in items:
            #self.dump(movie)
            #return
            li = self.create_film_item(movie)
            xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=False, listitem = li, url=self.plugin_dir+"?action=play&contentId=&cpId")
        xbmcplugin.endOfDirectory(handle = self.plugin_handle)

    def get_timvision_service_url (self):
        return 'http://127.0.0.1:' + str(self.kodi_helper.get_addon().getSetting('timvision_service_port'))
    def call_timvision_service (self, params):
        url_values = urllib.urlencode(params)
        url = self.get_timvision_service_url()
        full_url = url + '?' + url_values
        data = urllib2.urlopen(full_url).read()
        parsed_json = json.loads(data)
        result = parsed_json.get('result', None)
        return result