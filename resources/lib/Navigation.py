import sys
import json
import urlparse
import urllib
import urllib2
import xbmc
import xbmcgui
import xbmcplugin
from resources.lib import utils
from resources.lib import TimVisionAPI


class Navigation:
    def __init__(self, handle, plugin, kodi_helper):
        self.plugin_handle = handle
        self.plugin_dir = plugin
        self.kodi_helper = kodi_helper

    def router(self, parameters):
        if not self.verifica_login():
            self.kodi_helper.open_settings()
            return

        params = self.parameters_string_to_dict(parameters)
        params_count = len(params)
        if params_count == 0:
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
                    items = utils.call_timvision_service(
                        {"method": "load_movies", "begin": "0", "load_all": "true"})
                    self.add_items_to_folder(items)
                elif page == "SERIE TV":
                    category_id = params.get("category_id")
                    self.create_category_page(
                        pageId=category_id, ha_elenco=True, actionName='SERIE_ELENCO')
                elif page == "SERIE_ELENCO":
                    items = utils.call_timvision_service(
                        {"method": "load_series", "begin": "0", "load_all": "true"})
                    self.add_items_to_folder(items)
                elif page == "INTRATTENIMENTO":
                    category_id = params.get("category_id")
                    self.create_category_page(pageId=category_id)
                elif page == "BAMBINI":
                    category_id = params.get("category_id")
                    self.create_category_page(
                        pageId=category_id, ha_elenco=True, actionName='BAMBINI_ELENCO')
                elif page == "BAMBINI_ELENCO":
                    items = utils.call_timvision_service(
                        {"method": "load_kids", "begin": "0", "load_all": "true"})
                    self.add_items_to_folder(items)

            if params.has_key("action"):
                action = params.get("action")
                if action == "apri_serie":
                    id_serie = params.get("id_serie")
                    nome_serie = urllib.unquote(params.get("serieNome",""))
                    self.populate_serie_seasons(id_serie,nome_serie)
                elif action == "apri_stagione":
                    id_stagione = params.get("id_stagione")
                    items = utils.call_timvision_service(
                        {"method": "load_serie_episodes", "seasonId": id_stagione})
                    if self.add_items_to_folder(items):
                        folderTitle = "Stagione "+params.get("seasonNo")
                        xbmcplugin.setPluginCategory(self.plugin_handle, folderTitle)
                elif action == "play_item":
                    contentId = params.get("contentId")
                    videoType = params.get("videoType")
                    has_hd = params.get("has_hd", "false")
                    prefer_hd = utils.get_setting("prefer_hd")
                    start_offset = params.get("startPoint")
                    self.play_video(contentId, videoType, has_hd, prefer_hd, start_offset)
                elif action == "open_page":
                    uri = params.get("uri")
                    self.open_category_page(uri)
                elif action == "logout":
                    utils.call_timvision_service({"method":"logout"})
                elif action == "play_season_trailer":
                    contentId = params.get("contentId")
                    self.play_season_trailer(contentId)
                elif action == "search":
                    self.go_search()

    def verifica_login(self, count=0):
        logged = utils.call_timvision_service({"method":"is_logged"})
        if not logged:
            credentials = self.kodi_helper.get_credentials()
            if credentials["username"] != "" and credentials["password"] != "":
                logged = utils.call_timvision_service({"method":"login", "username":credentials["username"], "password":credentials["password"]})
            if not logged:
                if count == 0:
                    username = self.kodi_helper.show_text_field("Email")
                    password = self.kodi_helper.show_password_field()
                    self.kodi_helper.set_credentials(username, password)
                    return self.verifica_login(count+1)
        return logged
    def parameters_string_to_dict(self, parameters):
        return dict(urlparse.parse_qsl(parameters[1:]))

    def create_main_page(self):
        categories = utils.call_timvision_service({"method": "get_categories"})
        if categories == None:
            self.kodi_helper.show_dialog("Controlla di avere la connessione attiva. Se l'errore persiste, contatta lo sviluppatore del plugin", "Errore")
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
        
        #search item
        li = xbmcgui.ListItem(label="Cerca...")
        xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=self.plugin_dir+"?action=search", isFolder=True,listitem=li)

        xbmcplugin.endOfDirectory(handle=self.plugin_handle)

    def create_category_page(self, pageId, ha_elenco=False, actionName=''):
        if ha_elenco:
            li = xbmcgui.ListItem(label='Elenco completo')
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=self.plugin_dir + "?page=" + actionName, listitem=li, isFolder=True)

        pages = utils.call_timvision_service({"method": "get_page", "page": str(pageId)})
        if pages != None:
            for page in pages:
                layout = page["layout"]
                if layout == "SMALL_CARDS" or layout == "KIDS_COLLECTIONS":
                    if page["metadata"]["label"] == "TUTTI I TITOLI":
                        continue
                    li = xbmcgui.ListItem(label=page["metadata"]["label"].lower().capitalize())
                    url = self.plugin_dir + "?action=open_page&uri=" + urllib.quote_plus(page["retrieveItems"]["uri"])
                    xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=True, listitem=li, url=url)

        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return

    def open_category_page(self, action):
        action = urllib.unquote_plus(action)
        items = utils.call_timvision_service({"method": "get_contents", "url": action})
        self.add_items_to_folder(items)

    def video_get_mediatype(self, media):
        if media == "EPISODE":
            return "episode"
        elif media == "MOVIE_ITEM":
            return "movie"
        elif media == "SERIES_ITEM":
            return "tvshow"
        return "movie"
    def create_list_item(self, movie,contentId):
        is_episode = movie["layout"] == "EPISODE"
        is_hd = self.video_has_hd(movie)
        rating_s = str(float(movie["metadata"]["rating"])*2)
        mediatype = self.video_get_mediatype(movie["layout"])

        li = xbmcgui.ListItem(label=movie["metadata"]["title"])

        if isinstance(movie["metadata"]["directors"],list):
            director_string = movie["metadata"]["directors"]
        else:
            director_string = ""
            for director in movie["metadata"]["directors"]:
                if len(director_string) > 0:
                    director_string += ", "
                director_string+=director
        
        li.setInfo("video", {
            "year": str(movie["metadata"]["year"]),
            "rating": rating_s,
            "cast": movie["metadata"]["actors"],
            "director":director_string,
            "plot": movie["metadata"]["longDescription"],
            "plotoutline": movie["metadata"]["shortDescription"],
            "title": movie["metadata"]["title"],
            "duration": str(movie["metadata"]["duration"]),
            "genre": movie["metadata"]["genre"],
            "mediatype":mediatype
        })
        if is_episode:
            li.setInfo("video",
                       {
                           "episode": movie["metadata"]["episodeNumber"],
                           "season": movie["metadata"]["season"]
                       })
        
        li.setArt({
            "fanart": movie["metadata"]["bgImageUrl"],
            "poster": movie["metadata"]["imageUrl"]
        })
        startOffset = 0.0
        if "bookmark" in movie["metadata"] and movie["metadata"]["duration"]!=None:
            startOffset = float(str(movie["metadata"]["bookmark"]))
            li.setProperty('StartOffset', str(movie["metadata"]["bookmark"])+".0")
            #li.setProperty('StartPercent', str(percentage))

        if mediatype != "tvshow":
            li.setProperty("isPlayable","true")
            li.addStreamInfo("video",{'width': '768', 'height': '432'} if not is_hd else {'width': '1920', 'height': '1080'})
        
        return self.create_context_menu(contentId,li,mediatype), startOffset

    def create_context_menu(self, contentId, li, mediatype):
        """
        actions = []

        if mediatype != "tvshow":
            actions.append(["Altre opzioni",self.plugin_dir+"?action=other_options&contentId="+contentId])
            
        if mediatype == "tvshow_season":
            trailer_action = "XBMC.RunPlugin("+self.plugin_dir+"?action=play_season_trailer&contentId="+contentId+")"
            actions.append(["Trailer", trailer_action])
        
        li.addContextMenuItems(actions)
        """
        return li
    def is_content_item(self, l):
        return l == "SERIES_ITEM" or l == "MOVIE_ITEM" or l == "EPISODE" or l == "COLLECTION_ITEM"
    
    def video_has_hd(self, video):
        for videoType in video["metadata"]["videoType"]:
            if videoType == "HD":
                return True
        return False
    def is_folder(self, layout_item):
        return layout_item == "SERIES_ITEM" or layout_item == "COLLECTION_ITEM" or layout_item=="EDITORIAL_ITEM" or layout_item=="KIDS_ITEM"

    def add_items_to_folder(self, items):
        if items == None:
            self.kodi_helper.show_dialog("Errore in add_items_to_folder: items is None", "Add items to folder")
            utils.kodi_log("add_items_to_folder: items is None")
            return False
        if len(items) == 0:
            self.kodi_helper.show_dialog("Non sono presenti contenuti? Controlla su timvision.it e/o contatta lo sviluppatore del plugin", "Elenco vuoto")
            return False
        _is_episodes = False
        for container in items:
            layout_item=container["layout"]

            folder = self.is_folder(layout_item)

            if layout_item == "COLLECTION_ITEM" or layout_item=="EDITORIAL_ITEM" or layout_item=="KIDS_ITEM":
                li = xbmcgui.ListItem(container["metadata"]["title"])
                li.setArt({"poster": container["metadata"]["imageUrl"]})
                li.setInfo("video", {
                    "plot": container["metadata"]["longDescription"].replace("Personaggi Second Screen ",""),
                    "plotoutline": container["metadata"]["shortDescription"]
                })
                url = self.plugin_dir + "?action=open_page&uri=" + urllib.quote_plus(container["actions"][0]["uri"])
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=folder, listitem=li, url=url)
                pass
            elif layout_item == "SERIES_ITEM":
                contentId = container["metadata"]["contentId"]
                li,offset = self.create_list_item(container,contentId)
                title_unquoted = container["metadata"]["title"]
                if isinstance(title_unquoted,unicode):
                    title_unquoted=title_unquoted.encode("utf-8")
                title = urllib.quote(title_unquoted)
                url = "action=apri_serie&id_serie="+ container["id"]+"&serieNome="+title
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=folder, listitem=li, url=self.plugin_dir + "?" + url)
                pass
            elif layout_item=="MOVIE_ITEM" or layout_item=="EPISODE":
                videoType = "MOVIE" if layout_item == "MOVIE_ITEM" else "EPISODE"
                contentId = container["id"] if videoType == "MOVIE" else container["metadata"]["contentId"]
                li, offset = self.create_list_item(container,contentId)
                has_hd = self.video_has_hd(container)
                url = "action=play_item&contentId="+str(contentId)+"&videoType="+videoType+"&has_hd="+str(has_hd)+"&startPoint="+str(offset)
                if not _is_episodes and videoType == "EPISODE":
                    _is_episodes = True
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=folder, listitem=li, url=self.plugin_dir + "?" + url)
                pass
        
        if _is_episodes:
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_EPISODE)
        else:
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return True

    def populate_serie_seasons(self, serieId,serieNome):
        items = utils.call_timvision_service(
            {"method": "load_serie_seasons", "serieId": serieId})
        if items is None:
            self.kodi_helper.show_dialog("Errore in populate_serie_seasons: items is None", "Caricamento stagioni")
            utils.kodi_log("populate_serie_seasons: items is None. SerieId="+serieId+" serieNome="+serieNome)
            return
        count = len(items)
        if count == 0:
            self.kodi_helper.show_dialog("Non sono presenti stagioni? Controlla su timvision.it e/o contatta lo sviluppatore del plugin", "Possibile errore")
            return
        #xbmcplugin.setContent(self.plugin_handle, "tvshow")
        
        unique_season = utils.get_setting("unique_season")
        if count == 1 and unique_season:
            id_stagione = items[0]["metadata"]["contentId"]
            episodes = utils.call_timvision_service({"method": "load_serie_episodes", "seasonId": id_stagione})
            if self.add_items_to_folder(episodes):
                folderTitle = "Stagione "+str(items[0]["metadata"]["season"])
                xbmcplugin.setPluginCategory(self.plugin_handle, folderTitle)
            return

        xbmcplugin.setPluginCategory(self.plugin_handle, serieNome)
        for season in items:
            li = xbmcgui.ListItem(label="Stagione " + str(season["metadata"]["season"]))
            li.setArt({ "fanart": season["metadata"]["bgImageUrl"] })
            li = self.create_context_menu(season["metadata"]["contentId"], li, "tvshow_season")
            url = "action=apri_stagione&seasonNo="+str(season["metadata"]["season"])+"&id_stagione=" + season["metadata"]["contentId"]
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=self.plugin_dir+"?"+url, listitem=li, isFolder=True)
        
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)

    def go_search(self):
        keyword = self.kodi_helper.show_text_field("Keyword")
        if keyword == None or len(keyword) == 0:
            return False
        items = utils.call_timvision_service({"method":"search", "keyword":keyword})
        return self.add_items_to_folder(items)

    def play_season_trailer(self, contentId):
        #xbmc.executebuiltin("PlayMedia(%s,1)" % (trailer))
        url = utils.call_timvision_service({"method":"get_season_trailer", "contentId":contentId})
        if url != None:
            xbmc.executebuiltin("XBMC.RunPlugin(plugin://inputstream.adaptive?manifest_type=mpd&)" % (url))
            self.play(url)

    def play_video(self, contentId, videoType,hasHd="false",preferHD="false", startOffset = "0.0"):
        license_info = utils.call_timvision_service(
            {"method": "get_license_video", "contentId": contentId, "videoType": videoType,"prefer_hd":preferHD,"has_hd":hasHd})
        
        if utils.get_setting("inputstream_kodi17"):
            license_address = self.get_timvision_service_url()+"?action=get_license&license_url="+urllib.quote(license_info["widevine_url"])
        else:
            license_address = license_info["widevine_url"]
        
        if license_address == None:
            return False

        self.play(contentId, license_info["mpd_file"],license_address,"AVS_COOKIE="+license_info["avs_cookie"], startOffset)
              
    def play(self, contentId, url, licenseKey=None,licenseHeaders="",startOffset = "0.0"):
        inputstream_addon, is_enabled = self.kodi_helper.get_inputstream_addon()

        if inputstream_addon == None:
            utils.kodi_log("inputstream.adaptive not found")
            self.kodi_helper.show_dialog("L'addon inputstream.adaptive non e' installato o e' disabilitato", "Addon non trovato")
            return
        if not is_enabled:
            utils.kodi_log("inputstream.adaptive addon not enabled")
            self.kodi_helper.show_dialog("L'addon inputstream.adaptive deve essere abilitato per poter visualizzare i contenuti", "Addon disabilitato")
            return

        userAgent = utils.get_user_agent()
        play_item = xbmcgui.ListItem(path=url)
        play_item.setContentLookup(False)
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty(inputstream_addon + '.stream_headers',userAgent)
        play_item.setProperty(inputstream_addon + '.manifest_type', 'mpd')
        if licenseKey!=None:
            play_item.setProperty(inputstream_addon + '.license_type', 'com.widevine.alpha')
            play_item.setProperty(inputstream_addon + '.license_key', licenseKey+'|'+userAgent+'&'+licenseHeaders+'|R{SSM}|')
        utils.log_on_desktop_file("resume at: "+startOffset,"other.log")
           
        play_item.setProperty('inputstreamaddon', "inputstream.adaptive")

        startOffset = float(startOffset)
        if not utils.get_setting("always_resume"):
            #TODO chiedere se si vuole riprendere da startOffset
            startOffset = 0.0
        utils.call_timvision_service({"method":"set_playing_item", "url":url, "contentId":contentId, "time":startOffset})
        xbmcplugin.setResolvedUrl(handle=self.plugin_handle, succeeded=True, listitem=play_item)
