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
            # self.create_home_page()
            self.create_main_page()
        else:
            if params.has_key("page"):
                page = params.get("page")
                if page == "HOME":
                    category_id = params.get("category_id")
                    self.create_category_page(pageId=category_id)
                elif page == "CINEMA":
                    category_id = params.get("category_id")
                    self.create_category_page(
                        pageId=category_id, ha_elenco=True, actionName='CINEMA_ELENCO')
                elif page == "CINEMA_ELENCO":
                    items = self.call_timvision_service(
                        {"method": "load_movies", "begin": "0", "load_all": "true"})
                    self.add_items_to_folder(items)
                elif page == "SERIE TV":
                    category_id = params.get("category_id")
                    self.create_category_page(
                        pageId=category_id, ha_elenco=True, actionName='SERIE_ELENCO')
                elif page == "SERIE_ELENCO":
                    items = self.call_timvision_service(
                        {"method": "load_series", "begin": "0", "load_all": "true"})
                    self.add_items_to_folder(items)
                elif page == "INTRATTENIMENTO":
                    category_id = params.get("category_id")
                    self.create_category_page(pageId=category_id)
                    pass
                elif page == "BAMBINI":
                    category_id = params.get("category_id")
                    self.create_category_page(
                        pageId=category_id, ha_elenco=True, actionName='BAMBINI_ELENCO')
                    pass
                elif page == "BAMBINI_ELENCO":
                    items = self.call_timvision_service(
                        {"method": "load_kids", "begin": "0", "load_all": "true"})
                    self.add_items_to_folder(items)

            if params.has_key("action"):
                action = params.get("action")
                if action == "apri_serie":
                    id_serie = params.get("id_serie")
                    self.populate_serie_seasons(id_serie)
                elif action == "apri_stagione":
                    id_stagione = params.get("id_stagione")
                    items = self.call_timvision_service(
                        {"method": "load_serie_episodes", "seasonId": id_stagione})
                    self.add_items_to_folder(items)
                elif action == "play_item":
                    contentId = params.get("contentId")
                    videoType = params.get("videoType")
                    self.play_video(contentId, videoType)
                elif action == "open_page":
                    uri = params.get("uri")
                    self.open_category_page(uri)

    def parameters_string_to_dict(self, parameters):
        return dict(urlparse.parse_qsl(parameters[1:]))

    def create_main_page(self):
        categories = self.call_timvision_service({"method": "get_categories"})
        if categories == None:
            self.kodi_helper.show_message(
                "Controlla di avere la connessione attiva. Se l'errore persiste, contatta lo sviluppatore del plugin", "Errore")
            return
        for cat in categories:
            label = cat["metadata"]["label"]
            if label == "A NOLEGGIO":
                continue
            li = xbmcgui.ListItem(label=label.lower().capitalize())
            uri = cat["actions"][0]["uri"]
            pageId = uri[6:uri.find("?")]
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=self.plugin_dir +
                                        "?page=" + label + "&category_id=" + pageId, isFolder=True, listitem=li)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)

    def create_category_page(self, pageId, ha_elenco=False, actionName=''):
        if ha_elenco:
            li = xbmcgui.ListItem(label='Elenco completo')
            xbmcplugin.addDirectoryItem(
                handle=self.plugin_handle, url=self.plugin_dir + "?page=" + actionName, listitem=li, isFolder=True)

        pages = self.call_timvision_service(
            {"method": "get_page", "page": str(pageId)})
        if pages != None:
            for page in pages:
                if page["layout"] == "SMALL_CARDS":
                    if page["metadata"]["label"] == "TUTTI I TITOLI":
                        continue
                    li = xbmcgui.ListItem(
                        label=page["metadata"]["label"].lower().capitalize())
                    url = self.plugin_dir + "?action=open_page&uri=" + \
                        urllib.quote_plus(page["retrieveItems"]["uri"])
                    xbmcplugin.addDirectoryItem(
                        handle=self.plugin_handle, isFolder=True, listitem=li, url=url)

        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return

    def open_category_page(self, action):
        action = urllib.unquote_plus(action)
        items = self.call_timvision_service(
            {"method": "get_contents", "url": action})
        self.add_items_to_folder(items)

    def create_list_item(self, movie, is_episode=False):
        li = xbmcgui.ListItem(label=movie["metadata"]["title"])
        li.setInfo("video", {
            "year": str(movie["metadata"]["year"]),
            "rating": str((movie["metadata"]["rating"]) * 2),
            "cast": movie["metadata"]["actors"],
            #"director":movie["metadata"]["directors"][0],
            "plot": movie["metadata"]["longDescription"],
            "plotoutline": movie["metadata"]["shortDescription"],
            "title": movie["metadata"]["title"],
            "duration": str(movie["metadata"]["duration"]),
            "genre": movie["metadata"]["genre"]
        })
        li.setArt({
            "fanart": movie["metadata"]["bgImageUrl"],
            "poster": movie["metadata"]["imageUrl"]
        })
        if is_episode:
            li.setInfo("video",
                       {
                           "episode": movie["metadata"]["episodeNumber"],
                           "season": movie["metadata"]["season"]
                       })
        return li

    def is_content_item(self, l):
        return l == "SERIES_ITEM" or l == "MOVIE_ITEM" or l == "EPISODE"

    def add_items_to_folder(self, items):
        if items == None:
            return
        if len(items) == 0:
            self.kodi_helper.show_message(
                "Non sono presenti contenuti? Controlla su timvision.it e/o contatta lo sviluppatore del plugin", "Elenco vuoto")
            return
        _is_episodes = False
        for container in items:
            if not self.is_content_item(container["layout"]):
                continue
            folder = container["layout"] == "SERIES_ITEM"
            li = self.create_list_item(
                container, container["layout"] == "EPISODE")
            if folder:
                url = "action=apri_serie&id_serie=" + container["id"]
            else:
                videoType = "MOVIE" if container["layout"] == "MOVIE_ITEM" else "EPISODE"
                contentId = container["id"] if videoType == "MOVIE" else container["metadata"]["contentId"]
                li.setProperty('isPlayable', 'true')
                url = "action=play_item&contentId=" + \
                    str(contentId) + "&videoType=" + videoType
                if not _is_episodes and videoType == "EPISODE":
                    _is_episodes = True
            xbmcplugin.addDirectoryItem(
                handle=self.plugin_handle, isFolder=folder, listitem=li, url=self.plugin_dir + "?" + url)
        if _is_episodes:
            xbmcplugin.addSortMethod(
                self.plugin_handle, xbmcplugin.SORT_METHOD_EPISODE)
        else:
            xbmcplugin.addSortMethod(
                self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.addSortMethod(
                self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(
                self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
            xbmcplugin.addSortMethod(
                self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return True

    def populate_serie_seasons(self, serieId):
        items = self.call_timvision_service(
            {"method": "load_serie_seasons", "serieId": serieId})
        if items is None:
            self.kodi_helper.show_message("Si e' verificato un errore", "")
            return
        count = len(items)
        if count == 0:
            self.kodi_helper.show_message(
                "Non sono presenti stagioni? Controlla su timvision.it e/o contatta lo sviluppatore del plugin", "Possibile errore")
            return

        for season in items:
            if season["layout"] == "SEASON":
                li = xbmcgui.ListItem(
                    label="Stagione " + str(season["metadata"]["season"]))
                li.setArt({
                    "fanart": season["metadata"]["bgImageUrl"]
                })
                url = "action=apri_stagione&id_stagione=" + \
                    season["metadata"]["contentId"]
                xbmcplugin.addDirectoryItem(
                    handle=self.plugin_handle, url=self.plugin_dir + "?" + url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)

    def play_video(self, contentId, videoType):
        license_info = self.call_timvision_service(
            {"method": "get_license_video", "contentId": contentId, "videoType": videoType})
        if license_info == None:
            return
        cookie = license_info["AVS_COOKIE"]
        mpd = license_info["mpd_file"]
        license_address = license_info["widevine_url"]

        self.kodi_helper.log("AVS_COOKIE = " + cookie + "\nmpd = " +
                             mpd + "\n" + "widevine = " + license_address)

        inputstream_addon = self.kodi_helper.get_inputstream_addon()
        if inputstream_addon == None:
            self.kodi_helper.log("inputstream_addon not found")
            return

        play_item = xbmcgui.ListItem(path=mpd)  # manifest = mpd url
        play_item.setContentLookup(False)
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty(inputstream_addon + '.stream_headers',
                              'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0')
        play_item.setProperty(inputstream_addon +
                              '.license_type', 'com.widevine.alpha')
        play_item.setProperty(inputstream_addon + '.manifest_type', 'mpd')
        play_item.setProperty(inputstream_addon + '.license_key', license_address +
                              '||R{SSM}|' + 'AVS_COOKIE=' + cookie)  # '||b{SSM}!b{SID}|'
        play_item.setProperty('inputstreamaddon', "inputstream.adaptive")
        xbmcplugin.setResolvedUrl(
            handle=self.plugin_handle, succeeded=True, listitem=play_item)

    def get_timvision_service_url(self):
        return 'http://127.0.0.1:' + str(self.kodi_helper.get_addon().getSetting('timvision_service_port'))

    def call_timvision_service(self, params):
        url_values = urllib.urlencode(params)
        url = self.get_timvision_service_url()
        full_url = url + '?' + url_values
        self.kodi_helper.log(full_url, xbmc.LOGNOTICE)
        data = urllib2.urlopen(full_url).read()
        parsed_json = json.loads(data)
        result = parsed_json.get('result', None)
        return result
