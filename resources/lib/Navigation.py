try: #python 3
    from urllib.parse import unquote, unquote_plus, quote_plus
except: #python 2
    from urllib import unquote, unquote_plus, quote_plus
import xbmc
import xbmcgui
import xbmcplugin
import time
import webbrowser
from resources.lib import utils, Dialogs, TimVisionAPI, Logger, TimVisionObjects
from resources.lib import TimVisionLibrary
import inputstreamhelper

VIEW_MOVIES = "movies"
VIEW_TVSHOWS = "tvshows"
VIEW_SEASONS = "seasons"
VIEW_EPISODES = "episodes"
VIEW_FOLDERS = "folders"

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
            self.verify_version()
            self.create_main_page()
        else:
            if "page" in params:
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

            if "action" in params:
                action = params.get("action")
                if action == "full_list":
                    category = params.get("category")
                    items = utils.call_service("load_all_contents", {"begin": 0, "category": category})
                    self.add_items_to_folder(items)
                elif action == "apri_serie":
                    id_serie = params.get("id_serie")
                    nome_serie = unquote(params.get("serieNome", ""))
                    items = utils.call_service("get_show_content", {"contentId": id_serie, "contentType": TimVisionAPI.TVSHOW_CONTENT_TYPE_SEASONS})
                    if len(items) == 1 and utils.get_setting("unique_season"):
                        items = TimVisionObjects.parse_collection(items)
                        items = utils.call_service("get_show_content", {"contentId": items[0].content_id, "contentType":TimVisionAPI.TVSHOW_CONTENT_TYPE_EPISODES})
                    self.add_items_to_folder(items=items, title=nome_serie)
                elif action == "apri_stagione":
                    id_stagione = params.get("id_stagione")
                    items = utils.call_service("get_show_content", {"contentId": id_stagione, "contentType":TimVisionAPI.TVSHOW_CONTENT_TYPE_EPISODES})
                    season_no = params.get("seasonNo")
                    self.add_items_to_folder(items=items, title="Stagione %s" % (season_no))
                elif action == "play_item":
                    content_id = params.get("contentId")
                    video_type = params.get("videoType")
                    has_hd = params.get("has_hd", "false")
                    start_offset = params.get("startPoint")
                    duration = params.get("duration")
                    paused = self.increase_play_video_count()
                    self.play_video(content_id, video_type, has_hd, start_offset, duration, paused)
                elif action == "open_page":
                    uri = unquote_plus(params.get("uri")).replace("maxResults=30", "maxResults=50").replace("&addSeeMore=50", "")
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
                    response = utils.call_service("set_favourite", {"contentId": content_id, "value": value, "mediatype":mediatype})
                    if response:
                        dialog_title = utils.get_local_string(30033)
                        dialog_msg = utils.get_local_string(30034) if value else utils.get_local_string(30035)
                        Dialogs.show_message(dialog_msg, dialog_title, xbmcgui.NOTIFICATION_INFO)
                        xbmc.executebuiltin("Container.Refresh()")
                    else:
                        dialog_title = utils.get_local_string(30038)
                        dialog_msg = utils.get_local_string(30039)
                        Dialogs.show_dialog(dialog_msg, dialog_title)
                elif action == "search":
                    keyword = Dialogs.get_text_input(utils.get_local_string(30032))
                    if keyword != None and len(keyword) > 0:
                        items = utils.call_service("search", {"keyword":keyword})
                        return self.add_items_to_folder(items)
                elif action == "favourites":
                    items = utils.call_service("get_favourite")
                    return self.add_items_to_folder(items)
                elif action == "donation":
                    self.open_donation_page()
                elif action == "library":
                    library = TimVisionLibrary.TimVisionLibrary()
                    library.update(force=True)
                elif action == "library_kodi":
                    library = TimVisionLibrary.TimVisionLibrary()
                    library.check_db_integrity()
                    pass

    def verifica_login(self, count=0):
        logged = utils.call_service("is_logged")
        if not logged:
            email = utils.get_setting("username")
            password = utils.get_setting("password")
            if email != "" and password != "":
                logged = utils.call_service("login", {"username":email, "password":password})
            if not logged:
                if count == 0:
                    utils.set_setting("username", Dialogs.get_text_input(utils.get_local_string(30001)))
                    utils.set_setting("password", Dialogs.get_password_input())
                    return self.verifica_login(count+1)
        return logged

    def verify_version(self, force=False):
        major, _ = utils.get_kodi_version()
        if major >= 18:
            return True
        
        if not utils.get_setting("kodi_version_alert_shown") or force:
            dialog_title = utils.get_local_string(30040)
            dialog_msg = utils.get_local_string(30067)
            Dialogs.show_dialog(dialog_msg, dialog_title)
            utils.set_setting("kodi_version_alert_shown", "true")
        return False

    def create_main_page(self):
        error = False
        categories = utils.call_service("get_categories")
        if categories is None:
            error = True
        else:
            for cat in categories:
                label = cat["metadata"]["label"]
                if label in ["A NOLEGGIO", "SPORT"]:
                    continue
                list_item = xbmcgui.ListItem(label=label.lower().capitalize())
                uri = cat["actions"][0]["uri"]
                page_id = uri[6:uri.find("?")]
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=utils.url_join(self.plugin_dir, "?page=%s&category_id=%s" % (label, page_id)), isFolder=True, listitem=list_item)
        list_item = xbmcgui.ListItem(label='Preferiti')
        xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=utils.url_join(self.plugin_dir, "?action=favourites"), isFolder=True, listitem=list_item)
        list_item = xbmcgui.ListItem(label="Cerca...")
        xbmcplugin.addDirectoryItem(handle=self.plugin_handle, url=utils.url_join(self.plugin_dir, "?action=search"), isFolder=True, listitem=list_item)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)

        if error:
            dialog_title = utils.get_local_string(30038)
            dialog_msg = utils.get_local_string(30042)
            Dialogs.show_dialog(dialog_msg, dialog_title)

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
                url = utils.url_join(self.plugin_dir, "?action=open_page&uri=%s" % (quote_plus(page["retrieveItems"]["uri"])))
                xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=True, listitem=list_item, url=url)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        return

    def add_items_to_folder(self, items, title=''):
        if len(items) == 0:
            dialog_title = utils.get_local_string(30043)
            dialog_msg = utils.get_local_string(30044)
            Dialogs.show_dialog(dialog_msg, dialog_title)
            xbmcplugin.endOfDirectory(handle=self.plugin_handle)
            return False
        items = TimVisionObjects.parse_collection(items)
        movies = 0
        tvshows = 0
        episodes = 0
        seasons = 0
        for item in items:
            list_item, is_folder, url = item.get_list_item()
            xbmcplugin.addDirectoryItem(handle=self.plugin_handle, isFolder=is_folder, listitem=list_item, url=utils.url_join(self.plugin_dir, url))
            if item.mediatype == TimVisionObjects.ITEM_MOVIE:
                movies+=1
            elif item.mediatype == TimVisionObjects.ITEM_TVSHOW:
                tvshows+=1
            elif item.mediatype == TimVisionObjects.ITEM_SEASON:
                seasons+=1
            elif item.mediatype == TimVisionObjects.ITEM_EPISODE:
                episodes+=1
        
        if episodes > 0:
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_EPISODE)
            view_mode = VIEW_EPISODES
        else:
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
            xbmcplugin.addSortMethod(self.plugin_handle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
            if movies > 0:
                view_mode = VIEW_MOVIES
            elif tvshows > 0:
                view_mode = VIEW_TVSHOWS
            elif  seasons > 0:
                view_mode = VIEW_SEASONS
            else:
                view_mode = VIEW_FOLDERS
        if len(title) > 0:
            xbmcplugin.setPluginCategory(self.plugin_handle, title)
            
        if view_mode not in [VIEW_FOLDERS]:
            xbmcplugin.setContent(handle=self.plugin_handle, content=view_mode)
        xbmcplugin.endOfDirectory(handle=self.plugin_handle)
        self.set_custom_view(view_mode)
        return True

    def set_custom_view(self, content):
        if utils.get_setting("custom_view_enabled"):
            if utils.get_setting("custom_skin_enabled"):
                view_id = utils.get_setting("view_skin_"+content)
            else:
                view = utils.get_setting('view_' + content)
                view_id = self.get_view_id(view, content)
            xbmc.executebuiltin('Container.SetViewMode(%s)' % str(view_id))

    def play_trailer(self, content_id, trailer_type):
        url = None
        if trailer_type == "MOVIE":
            url = utils.call_service("get_movie_trailer", {"contentId":content_id})
        elif trailer_type == "TVSHOW":
            url = utils.call_service("get_season_trailer", {"contentId":content_id})
        if url != None:
            self.play(url=url)
        else:
            dialog_title = utils.get_local_string(30036)
            dialog_msg = utils.get_local_string(30037)
            Dialogs.show_message(dialog_msg, dialog_title)

    def play_video(self, content_id, video_type, has_hd=False, start_offset=0.0, duration=0, paused=False):
        if not self.verify_version(True):
            return
        license_info = utils.call_service("get_license_video", {"contentId": content_id, "videoType": video_type, "has_hd":has_hd})
        if license_info is None:
            dialog_msg = utils.get_local_string(30045)
            Dialogs.show_dialog(dialog_msg)
            return
        user_agent = utils.get_user_agent()
        headers = "%s&AVS_COOKIE=%s&Connection=keep-alive" % (user_agent, license_info["avs_cookie"])
        self.play(content_id, license_info["mpd_file"], license_info["widevine_url"], headers, start_offset, video_type, duration, paused)

    def play(self, content_id=None, url=None, license_key=None, license_headers="", start_offset=0.0, content_type='', duration=0, start_paused=False):
        PROTOCOL = 'mpd'
        DRM = 'com.widevine.alpha'
        user_agent = utils.get_user_agent()

        play_item = xbmcgui.ListItem(path=url)
        play_item.setContentLookup(False)
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty('inputstreamaddon', "inputstream.adaptive")
        play_item.setProperty('inputstream.adaptive.stream_headers', "%s&Connection=keep-alive" % (user_agent))
        play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
        
        if license_key != None:
            is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
            if not is_helper.check_inputstream():
                Dialogs.show_dialog(utils.get_local_string(30063))
                return
            play_item.setProperty('inputstream.adaptive.license_type', DRM)
            play_item.setProperty('inputstream.adaptive.license_key', license_key+'|'+license_headers+'|R{SSM}|')
            
            start_offset = int(start_offset)
            duration = int(duration)
            if start_offset >= 10 and duration-start_offset > 30:
                if not utils.get_setting("always_resume"):
                    xbmc.executebuiltin("Dialog.Close(all,true)")
                    dialog_title = utils.get_local_string(30050)
                    message = utils.get_local_string(30051) % (utils.get_timestring_from_seconds(start_offset))
                    start_offset = start_offset if Dialogs.ask(message, dialog_title) else 0
            else:
                start_offset = 0
            
            utils.call_service("set_playing_item", {"url":url, "contentId":content_id, "time":start_offset, "videoType":content_type, "duration":duration, "paused":start_paused})
            xbmcplugin.setResolvedUrl(handle=self.plugin_handle, succeeded=True, listitem=play_item)
        else:
            xbmc.Player().play(item=url, listitem=play_item)
    
    def get_view_id(self, view_id, kind):
        view_id = int(view_id)
        if(kind == VIEW_MOVIES):
            # 30016|30017|30018|30019|30020|30021|30022
            if view_id == 0: #30016 - widelist
                return 55
            elif view_id == 1: #30017 iconwall
                return 52
            elif view_id == 2: #30018 fanart
                return 502
            elif view_id == 3: #19 list
                return 50
            elif view_id == 4: #20 poster
                return 51
            elif view_id == 5: #21 shift
                return 53
            elif view_id == 6: #22 infowall
                return 54
        elif (kind == VIEW_TVSHOWS):
            if view_id == 0: #30016 - widelist
                return 55
            elif view_id == 1: #30017 iconwall
                return 52
            elif view_id == 2: #30018 fanart
                return 502
            elif view_id == 3: #19 list
                return 50
            elif view_id == 4: #20 poster
                return 51
            elif view_id == 5: #21 shift
                return 53
            elif view_id == 6: #22 infowall
                return 54
            elif view_id == 7: #23 banner
                return 501
        elif kind == VIEW_SEASONS:
            if view_id == 0: #30016 - widelist
                return 55
            elif view_id == 1: #30017 iconwall
                return 52
            elif view_id == 2: #30018 fanart
                return 502
            elif view_id == 3: #19 list
                return 50
            elif view_id == 4: #20 poster
                return 51
            elif view_id == 5: #21 shift
                return 53
            elif view_id == 6: #22 infowall
                return 54
            elif view_id == 7: #31 wall
                return 500
        elif kind == VIEW_EPISODES:
            if view_id == 0: #30016 - widelist
                return 55
            elif view_id == 1: #30017 iconwall
                return 52
        return 55
    
    def increase_play_video_count(self):
        show_donation_enabled = utils.get_setting("timvision_show_donation", "true")
        play_video_count = int(utils.get_setting("timvision_start_count", "0"))
        pause_video = False
        if show_donation_enabled:
            if play_video_count > 0 and play_video_count % 100 == 0:
                dialog_title = utils.get_local_string(30064)
                dialog_message = utils.get_local_string(30065)
                if Dialogs.ask(dialog_message, dialog_title):
                    pause_video = self.open_donation_page()
        
        play_video_count = play_video_count + 1
        utils.set_setting("timvision_start_count", str(play_video_count))
        return pause_video
    
    def open_donation_page(self):
        try:
            webbrowser.open_new_tab("https://www.paypal.me/pinoelefante")
            return True
        except:
            Dialogs.show_dialog("https://www.paypal.me/pinoelefante")
            return False
