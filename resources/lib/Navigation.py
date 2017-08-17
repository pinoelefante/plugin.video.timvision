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
            if params.has_key("action"):
                action = params.get("action")
                if action == "apri_serie":
                    id_serie = params.get("id_serie")
                    self.populate_serie_seasons(id_serie)
                if action == "apri_stagione":
                    id_stagione = params.get("id_stagione")
                    self.populate_serie_episodes(id_stagione)
                if action == "play":
                    contentId = params.get("contentId")
                    videoType = params.get("videoType")
                    self.play_video(contentId, videoType)
                    #self.kodi_helper.show_message("Non implementato ancora","")
                    return
    
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
    
    def create_list_item(self, movie):
        li = xbmcgui.ListItem(label=movie["metadata"]["title"])
        #li.addStreamInfo("video",{'duration':int(movie["metadata"]["duration"])})
        li.setInfo("video", {
            #"year":int(movie["metadata"]["year"]),
            #"rating":float(movie["metadata"]["rating"])*2,
            "cast":movie["metadata"]["actors"],
            #"director":movie["metadata"]["directors"][0],
            "plot":movie["metadata"]["longDescription"],
            "plotoutline":movie["metadata"]["shortDescription"],
            "title":movie["metadata"]["title"],
            "duration":movie["metadata"]["duration"],
            "genre":movie["metadata"]["genre"]
        })
        li.setArt({
            "fanart":movie["metadata"]["bgImageUrl"],
            "poster":movie["metadata"]["imageUrl"]
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
                url = "action=play&contentId="+video["id"]+"&videoType=MOVIE"
            xbmcplugin.addDirectoryItem(handle = self.plugin_handle, isFolder=True, listitem = li, url=self.plugin_dir+"?"+url)
        xbmcplugin.endOfDirectory(handle = self.plugin_handle)
    
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
                li = xbmcgui.ListItem(label=episode["metadata"]["episodeNumber"]+"-"+episode["metadata"]["title"])
                li.setArt({
                    "fanart":episode["metadata"]["bgImageUrl"],
                    "poster":episode["metadata"]["imageUrl"]
                })
                li.setInfo("video", 
                {
                    "plot":episode["metadata"]["longDescription"],
                    "plotoutline":episode["metadata"]["shortDescription"],
                    "title":episode["metadata"]["title"],
                    "duration":str(episode["metadata"]["duration"]),
                    "genre":episode["metadata"]["genre"],
                    "episode": episode["metadata"]["episodeNumber"],
                    "season": episode["metadata"]["season"]
                })
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle,url=self.plugin_dir+"?action=play&videoType=EPISODE&contentId="+episode["metadata"]["contentId"],isFolder=True,listitem=li)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
    def play_video(self, contentId, videoType):
        license_info = self.call_timvision_service({"method":"get_license_video", "contentId":contentId, "videoType":videoType})
        if license_info is None:
            return
        cookie = license_info["AVS_COOKIE"]
        mpd = license_info["mpd_file"]
        license_address = license_info["widevine_url"]

        inputstream_addon = self.get_inputstream_addon()
        if inputstream_addon == None:
            self.kodi_helper.log("inputstream_addon not found")
            return

        play_item = xbmcgui.ListItem(path=mpd, label='Play') #manifest = mpd url
        play_item.setContentLookup(False)
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty(inputstream_addon + '.stream_headers', 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0&AVS_COOKIE='+cookie)        
        play_item.setProperty(inputstream_addon + '.license_type', 'com.widevine.alpha')
        play_item.setProperty(inputstream_addon + '.manifest_type', 'mpd')
        play_item.setProperty(inputstream_addon + '.license_key', license_address)
        #play_item.setProperty(inputstream_addon + '.server_certificate', 'Cr0CCAMSEOVEukALwQ8307Y2+LVP+0MYh/HPkwUijgIwggEKAoIBAQDm875btoWUbGqQD8eAGuBlGY+Pxo8YF1LQR+Ex0pDONMet8EHslcZRBKNQ/09RZFTP0vrYimyYiBmk9GG+S0wB3CRITgweNE15cD33MQYyS3zpBd4z+sCJam2+jj1ZA4uijE2dxGC+gRBRnw9WoPyw7D8RuhGSJ95OEtzg3Ho+mEsxuE5xg9LM4+Zuro/9msz2bFgJUjQUVHo5j+k4qLWu4ObugFmc9DLIAohL58UR5k0XnvizulOHbMMxdzna9lwTw/4SALadEV/CZXBmswUtBgATDKNqjXwokohncpdsWSauH6vfS6FXwizQoZJ9TdjSGC60rUB2t+aYDm74cIuxAgMBAAE6EHRlc3QubmV0ZmxpeC5jb20SgAOE0y8yWw2Win6M2/bw7+aqVuQPwzS/YG5ySYvwCGQd0Dltr3hpik98WijUODUr6PxMn1ZYXOLo3eED6xYGM7Riza8XskRdCfF8xjj7L7/THPbixyn4mULsttSmWFhexzXnSeKqQHuoKmerqu0nu39iW3pcxDV/K7E6aaSr5ID0SCi7KRcL9BCUCz1g9c43sNj46BhMCWJSm0mx1XFDcoKZWhpj5FAgU4Q4e6f+S8eX39nf6D6SJRb4ap7Znzn7preIvmS93xWjm75I6UBVQGo6pn4qWNCgLYlGGCQCUm5tg566j+/g5jvYZkTJvbiZFwtjMW5njbSRwB3W4CrKoyxw4qsJNSaZRTKAvSjTKdqVDXV/U5HK7SaBA6iJ981/aforXbd2vZlRXO/2S+Maa2mHULzsD+S5l4/YGpSt7PnkCe25F+nAovtl/ogZgjMeEdFyd/9YMYjOS4krYmwp3yJ7m9ZzYCQ6I8RQN4x/yLlHG5RH/+WNLNUs6JAZ0fFdCmw=')
        play_item.setProperty('inputstreamaddon', inputstream_addon)
        xbmcplugin.addDirectoryItem(listitem=play_item, url=mpd, isFolder=False, handle=self.plugin_handle)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        # check if we have a bookmark e.g. start offset position
        '''
        if int(start_offset) > 0:
            play_item.setProperty('StartOffset', str(start_offset) + '.0')
        # set infoLabels
        if len(infoLabels) > 0:
            play_item.setInfo('video',  infoLabels)
        '''
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