import urllib
import xbmc, xbmcgui, xbmcplugin
from resources.lib import utils, Dialogs, TimVisionAPI, Logger, TimVisionObjects

class Navigation(object):
    def __init__(self, handle, plugin):
        self.plugin_handle = handle
        self.plugin_dir = plugin

    def router(self, parameters):
        if not self.verifica_login():
            utils.open_settings()
            return

        params = utils.get_parameters_dict_from_url(parameters)
        params_count = len(params)
        if params_count == 0:
            self.create_main_page()
        else:
            if params.has_key("page"):
                page = params.get("page")
                category_id = params.get("category_id")
                if page in ["HOME", "INTRATTENIMENTO"]:
                    self.create_category_page(page_id=category_id)
                elif page == "CINEMA":
                    self.create_category_page(page_id=category_id, ha_elenco=True, category_name='Cinema')
                elif page == "SERIE TV":
                    self.create_category_page(page_id=category_id, ha_elenco=True, category_name='Serie')
                elif page == "BAMBINI":
                    self.create_category_page(page_id=category_id, ha_elenco=True, category_name='Kids')

            if params.has_key("action"):
                action = params.get("action")
                if action == "full_list":
                    category = params.get("category")
                    items = utils.call_service("load_all_contents", {"begin": 0, "category": category})
                    self.add_items_to_folder(items)
                elif action == "apri_serie":
                    id_serie = params.get("id_serie")
                    nome_serie = urllib.unquote(params.get("serieNome", ""))
                    items = utils.call_service("get_show_content", {"contentId": id_serie, "contentType": TimVisionAPI.TVSHOW_CONTENT_TYPE_SEASONS})
                    if len(items) == 1 and utils.get_setting("unique_season"):
                        items = TimVisionObjects.parse_collection(items)
                        items = utils.call_service("get_show_content", {"contentId": items[0].content_id, "contentType":TimVisionAPI.TVSHOW_CONTENT_TYPE_EPISODES})
                    self.add_items_to_folder(items=items, title=nome_serie)
                elif action == "apri_stagione":
                    id_stagione = params.get("id_stagione")
                    items = utils.call_service("get_show_content", {"contentId": id_stagione, "contentType":TimVisionAPI.TVSHOW_CONTENT_TYPE_EPISODES})
                    season_no = params.get("seasonNo")
                    self.add_items_to_folder(items=items, is_episodes=True, title="Stagione %s" % (season_no))
                elif action == "play_item":
                    content_id = params.get("contentId")
                    video_type = params.get("videoType")
                    has_hd = params.get("has_hd", "false")
                    start_offset = params.get("startPoint")
                    duration = params.get("duration")
                    self.play_video(content_id, video_type, has_hd, start_offset, duration)
                elif action == "open_page":
                    uri = urllib.unquote_plus(params.get("uri")).replace("maxResults=30", "maxResults=50").replace("&addSeeMore=50", "")
                    items = utils.call_service("get_contents", {"url": uri})
                    items = [x for x in items if x["layout"] != "SEE_MORE"]
                    self.add_items_to_folder(items)
                elif action == "logout":
                    utils.call_service("logout")
                elif  action == "play_trailer":
                    content_id = params.get("contentId")
                    content_type = params.get("type")
                    self.play_trailer(content_id, content_type)
                elif action == "set_seen":
                    content_id = params.get("contentId")
                    duration = params.get("duration")
                    utils.call_service("set_content_seen", {"contentId":content_id, "duration":duration})
                    xbmc.executebuiltin("Container.Refresh()")
                elif action == "toogle_favourite":
                    content_id = params.get("contentId")
                    value = utils.get_bool(params.get("value"))
                    mediatype = params.get("mediatype")
                    utils.call_service("set_favourite", {"contentId": content_id, "value": value, "mediatype":mediatype})
                    xbmc.executebuiltin("Container.Refresh()")
                elif action == "search":
                    keyword = Dialogs.get_text_input("Keyword")
                    if keyword != None and len(keyword) > 0:
                        items = utils.call_service("search", {"keyword":keyword})
                        return self.add_items_to_folder(items)

    def verifica_login(self, count=0):
        logged = utils.call_service("is_logged")
        if not logged:
            email = utils.get_setting("username")
            password = utils.get_setting("password")
            if email != "" and password != "":
                logged = utils.call_service("login", {"username":email, "password":password})
            if not logged:
                if count == 0:
                    utils.set_setting("username", Dialogs.get_text_input("Email"))
                    utils.set_setting("password", Dialogs.get_password_input())
                    return self.verifica_login(count+1)
        return logged

    def create_main_page(self):
        categories = utils.call_service("get_categories")
        if categories is None:
            Dialogs.show_dialog("Controlla di avere la connessione attiva. Se l'errore persiste, contatta lo sviluppatore del plugin", "Errore")
            return
        for cat in categories:
            label = cat["metadata"]["label"]
            if label == "A NOLEGGIO":
                continue
            list_item = xbmcgui.ListItem(label=label.lower().capitalize())
            uri = cat["actions"][0]["uri"]
            page_id = uri[6:uri.find("?")]
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=utils.url_join(self.plugin_dir, "?page=%s&category_id=%s" % (label, page_id)), isFolder=True, listitem=list_item)

        list_item = xbmcgui.ListItem(label="Cerca...")
        xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=utils.url_join(self.plugin_dir, "?action=search"), isFolder=True, listitem=list_item)

        xbmcplugin.endOfDirectory(handle=self.plugin_handle)

    def create_category_page(self, page_id, ha_elenco=False, category_name=''):
        if ha_elenco:
            list_item = xbmcgui.ListItem(label='Elenco completo')
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=utils.url_join(self.plugin_dir, "?action=full_list&category=%s" % (category_name)), listitem=list_item, isFolder=True)

        pages = utils.call_service("get_page", {"page": str(page_id)})
        if pages != None:
            pages = [page for page in pages if page["layout"] in ["SMALL_CARDS", "KIDS_COLLECTIONS"]]
            for page in pages:
                if page["metadata"]["label"] == "TUTTI I TITOLI":
                    continue
                list_item = xbmcgui.ListItem(label=page["metadata"]["label"].lower().capitalize())
                url = utils.url_join(self.plugin_dir, "?action=open_page&uri=%s" % (urllib.quote_plus(page["retrieveItems"]["uri"])))
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=True, listitem=list_item, url=url)

        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return

    def add_items_to_folder(self, items, is_episodes=False, title=''):
        if len(items) == 0:
            Dialogs.show_dialog("Non sono presenti contenuti? Controlla su timvision.it e/o contatta lo sviluppatore del plugin", "Elenco vuoto")
            return False
        items = TimVisionObjects.parse_collection(items)
        for item in items:
            list_item, is_folder, url = item.get_list_item()
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=is_folder, listitem=list_item, url=utils.url_join(self.plugin_dir, url))

        if is_episodes:
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_EPISODE)
        else:
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
        if len(title) > 0:
            xbmcplugin.setPluginCategory(self.plugin_handle, title)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return True

    def play_trailer(self, content_id, trailer_type):
        url = None
        if trailer_type == "MOVIE":
            url = utils.call_service("get_movie_trailer", {"contentId":content_id})
        elif trailer_type == "TVSHOW":
            url = utils.call_service("get_season_trailer", {"contentId":content_id})
        if url != None:
            self.play(url=url)
        else:
            Dialogs.show_message("Il contenuto non ha un trailer", "Trailer assente")

    def play_video(self, content_id, video_type, has_hd=False, start_offset=0.0, duration=0):
        license_info = utils.call_service("get_license_video", {"contentId": content_id, "videoType": video_type, "has_hd":has_hd})
        if license_info is None:
            #TODO try get ism manifest
            Dialogs.show_dialog("Si e' verificato un errore o non e' possibile vedere il contenuto su questo dispositivo")
            return
        self.play(content_id, license_info["mpd_file"], license_info["widevine_url"], "AVS_COOKIE="+license_info["avs_cookie"], start_offset, video_type, duration)

    def play(self, content_id=None, url=None, license_key=None, license_headers="", start_offset=0.0, content_type='', duration=0):
        inputstream, is_enabled = utils.get_addon('inputstream.adaptive')

        if inputstream is None:
            Logger.kodi_log("inputstream.adaptive not found")
            Dialogs.show_dialog("L'addon inputstream.adaptive non e' installato o e' disabilitato", "Addon non trovato")
            return
        if not is_enabled:
            Logger.kodi_log("inputstream.adaptive addon not enabled")
            Dialogs.show_dialog("L'addon inputstream.adaptive deve essere abilitato per poter visualizzare i contenuti", "Addon disabilitato")
            return

        user_agent = utils.get_user_agent()
        play_item = xbmcgui.ListItem(path=url)
        play_item.setContentLookup(False)
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty(inputstream + '.stream_headers', user_agent)
        play_item.setProperty(inputstream + '.manifest_type', 'mpd')
        play_item.setProperty('inputstreamaddon', "inputstream.adaptive")

        if license_key != None:
            play_item.setProperty(inputstream + '.license_type', 'com.widevine.alpha')
            play_item.setProperty(inputstream + '.license_key', license_key+'|'+user_agent+'&'+license_headers+'|R{SSM}|')
            if not utils.get_setting("always_resume") and float(start_offset) > 10:
                message = "Vuoi riprendere la visione da %s?" % (utils.get_timestring_from_seconds(float(start_offset)))
                start_offset = start_offset if Dialogs.ask(message, "Riprendi visione") else 0.0
            utils.call_service("set_playing_item", {"url":url, "contentId":content_id, "time":start_offset, "videoType":content_type, "duration":duration})
            xbmcplugin.setResolvedUrl(handle=self.plugin_handle, succeeded=True, listitem=play_item)
        else:
            xbmc.Player().play(item=url, listitem=play_item)
