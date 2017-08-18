import sys
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
                    items = self.call_timvision_service({"method":"recommended_video", "category":page})
                    self.add_items_to_folder(items)
                if page == "CINEMA":
                    pass
                if page == "SERIETV":
                    pass
                if page == "INTRATTENIMENTO":
                    pass
                if page == "KIDS":
                    pass
            if params.has_key("action"):
                action = params.get("action")
                if action == "apri_serie":
                    id_serie = params.get("id_serie")
                    self.populate_serie_seasons(id_serie)
                if action == "apri_stagione":
                    id_stagione = params.get("id_stagione")
                    self.populate_serie_episodes(id_stagione)
                if action == "play_item":
                    contentId = params.get("contentId")
                    videoType = params.get("videoType")
                    self.play_video(contentId, videoType)
                    return
    
    def parameters_string_to_dict(self, parameters):
        return dict(urlparse.parse_qsl(parameters[1:]))

    def create_home_page(self):
        recomDir = xbmcgui.ListItem(label='Raccomandati')
        xbmcplugin.addDirectoryItem(isFolder=True, handle = self.plugin_handle, listitem = recomDir, url=self.plugin_dir+"?page=RECOMMENDED")
        cinemaDir = xbmcgui.ListItem(label='Cinema')
        xbmcplugin.addDirectoryItem(isFolder=True, handle=self.plugin_handle,listitem=cinemaDir,url=self.plugin_dir+"?page=CINEMA")
        serieDir = xbmcgui.ListItem(label='Serie TV')
        xbmcplugin.addDirectoryItem(isFolder=True, handle=self.plugin_handle,listitem=serieDir,url=self.plugin_dir+"?page=SERIETV")
        intrattenimentoDir = xbmcgui.ListItem(label='Intrattenimento')
        xbmcplugin.addDirectoryItem(isFolder=True, handle=self.plugin_handle,listitem=intrattenimentoDir,url=self.plugin_dir+"?page=INTRATTENIMENTO")
        kidDir = xbmcgui.ListItem(label='Bambini')
        xbmcplugin.addDirectoryItem(isFolder=True, handle=self.plugin_handle,listitem=kidDir,url=self.plugin_dir+"?page=KIDS")
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
    
    def create_list_item(self, movie, is_episode = False):
        li = xbmcgui.ListItem(label=movie["metadata"]["title"])
        li.setInfo("video", {
            "year":str(movie["metadata"]["year"]),
            "rating":str((movie["metadata"]["rating"])*2),
            "cast":movie["metadata"]["actors"],
            #"director":movie["metadata"]["directors"][0],
            "plot":movie["metadata"]["longDescription"],
            "plotoutline":movie["metadata"]["shortDescription"],
            "title":movie["metadata"]["title"],
            "duration":str(movie["metadata"]["duration"]),
            "genre":movie["metadata"]["genre"]
        })
        li.setArt({
            "fanart":movie["metadata"]["bgImageUrl"],
            "poster":movie["metadata"]["imageUrl"]
        })
        if is_episode:
            li.setLabel(episode["metadata"]["episodeNumber"]+" - "+movie["metadata"]["title"])
            li.setInfo("video", 
            {
                "episode": episode["metadata"]["episodeNumber"],
                "season": episode["metadata"]["season"]
            })
        return li

    def populate_recommended_folder(self,page_type):
        items = self.call_timvision_service({"method":"recommended_video", "category":page_type})
        if items is None:
            self.kodi_helper.show_message("Si e' verificato un errore", "")
            return

        count = len(items)
        if count == 0:
            self.kodi_helper.show_message("Non sono presenti contenuti","Elenco vuoto")
            return

        for video in items:
            folder = video["layout"] == "SERIES_ITEM"
            li = self.create_list_item(video)
            if folder:
                url = "action=apri_serie&id_serie="+video["id"]
            else:
                li.setProperty('isPlayable', 'true')
                url = "action=play_item&contentId="+video["id"]+"&videoType=MOVIE"
            xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=folder, listitem = li, url=self.plugin_dir+"?"+url)
        xbmcplugin.endOfDirectory(handle = self.plugin_handle)
        return True
    def add_items_to_folder(self, items):
        if items == None:
            return
        if len(items) == 0:
            self.kodi_helper.show_message("Non sono presenti contenuti","Elenco vuoto")
            return

        for container in items:
            folder = container["layout"] == "SERIES_ITEM"
            li = self.create_list_item(video)
            if folder:
                url = "action=apri_serie&id_serie="+container["id"]
            else:
                videoType = "MOVIE" if video["layout"]=="MOVIE_ITEM" else "EPISODE"
                li.setProperty('isPlayable', 'true')
                url = "action=play_item&contentId="+video["id"]+"&videoType="+videoType
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle,isFolder=folder, listitem=li, url=self.plugin_dir+"?"+url)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return True
    def populate_serie_seasons(self, serieId):
        items = self.call_timvision_service({"method":"load_serie_seasons", "serieId":serieId})
        if items is None:
            self.kodi_helper.show_message("Si e' verificato un errore", "")
            return
        count = len(items)
        if count == 0:
            self.kodi_helper.show_message("Non sono presenti stagioni? Controlla su timvision.it e/o contatta lo sviluppatore del plugin","Possibile errore")
            return

        for season in items:
            if season["layout"] == "SEASON":
                li = xbmcgui.ListItem(label="Stagione "+str(season["metadata"]["season"]))
                li.setArt({
                    "fanart":season["metadata"]["bgImageUrl"]
                })
                url = "action=apri_stagione&id_stagione="+season["metadata"]["contentId"]
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=self.plugin_dir+"?"+url,listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
    def populate_serie_episodes(self, seasonId):
        items = self.call_timvision_service({"method":"load_serie_episodes", "seasonId":seasonId})
        if items is None:
            self.kodi_helper.show_message("Si e' verificato un errore", "")
            return
        count = len(items)
        if count == 0:
            self.kodi_helper.show_message("Non sono presenti episodi? Controlla su timvision.it e/o contatta lo sviluppatore del plugin","Possibile errore")
            return
        for episode in items:
            if episode["layout"] == "EPISODE":
                li = self.create_list_item(episode, True)
                li.setProperty('isPlayable', 'true')
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle,url=self.plugin_dir+"?action=play_item&videoType=EPISODE&contentId="+episode["metadata"]["contentId"],isFolder=False,listitem=li)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return True

    def play_video(self, contentId, videoType):
        license_info = self.call_timvision_service({"method":"get_license_video", "contentId":contentId, "videoType":videoType})
        if license_info == None:
            return
        cookie = license_info["AVS_COOKIE"]
        mpd = license_info["mpd_file"]
        license_address = license_info["widevine_url"]

        self.kodi_helper.log("AVS_COOKIE = "+cookie+"\nmpd = "+mpd+"\n"+"widevine = "+license_address)

        inputstream_addon = self.get_inputstream_addon()
        if inputstream_addon == None:
            self.kodi_helper.log("inputstream_addon not found")
            return

        play_item = xbmcgui.ListItem(path=mpd) #manifest = mpd url
        play_item.setContentLookup(False)
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty(inputstream_addon + '.stream_headers', 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0&AVS_COOKIE='+cookie)        
        play_item.setProperty(inputstream_addon + '.license_type', 'com.widevine.alpha')
        play_item.setProperty(inputstream_addon + '.manifest_type', 'mpd')
        play_item.setProperty(inputstream_addon + '.license_key', license_address +'||R{SSM}|') #'||b{SSM}!b{SID}|'
        play_item.setProperty('inputstreamaddon', "inputstream.adaptive")
        xbmcplugin.setResolvedUrl(handle=self.plugin_handle, succeeded=True, listitem=play_item)
        
    def get_inputstream_addon(self):
        type = 'inputstream.adaptive'
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': type,
                'properties': ['enabled']
            }
        }
        response = xbmc.executeJSONRPC(json.dumps(payload))
        data = json.loads(response)
        if not 'error' in data.keys():
            if data['result']['addon']['enabled']:
                return type
        return None
    def get_timvision_service_url (self):
        return 'http://127.0.0.1:' + str(self.kodi_helper.get_addon().getSetting('timvision_service_port'))
    def call_timvision_service (self, params):
        url_values = urllib.urlencode(params)
        url = self.get_timvision_service_url()
        full_url = url + '?' + url_values
        self.kodi_helper.log(full_url, xbmc.LOGNOTICE)
        data = urllib2.urlopen(full_url).read()
        parsed_json = json.loads(data)
        result = parsed_json.get('result', None)
        return result