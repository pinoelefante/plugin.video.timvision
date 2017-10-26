import urllib
from resources.lib import utils

class TimVisionHttpSubRessourceHandler:
    """ Represents the callable internal server routes & translates/executes them to requests for Netflix"""

    def __init__(self, kodi_helper, timvision_session):
        self.kodi_helper = kodi_helper
        self.timvision_session = timvision_session
        #self.prefetch_login()

    def prefetch_login(self):
        credentials = self.kodi_helper.get_credentials()
        user = credentials.get('username')
        passw = credentials.get('password')
        if user != '' and passw != '':
            self.timvision_session.login(user, passw)

    def is_logged(self, params):
        return self.timvision_session.is_logged()

    def login(self, params):
        email = params.get('username', [''])[0]
        password = params.get('password', [''])[0]
        if email != '' and password != '':
            return self.timvision_session.login(email, password)
        return None
    
    def logout(self, params):
        return self.timvision_session.logout()

    def load_serie_seasons(self, params):
        serieId = params.get('serieId')[0]
        return self.timvision_session.load_serie_seasons(serieId)

    def load_serie_episodes(self, params):
        seasonId = params.get('seasonId')[0]
        return self.timvision_session.load_serie_episodes(seasonId)

    def get_license_video(self, params):
        contentid = params.get("contentId")[0]
        videoType = params.get("videoType")[0]
        prefer_hd = utils.get_bool(params.get("prefer_hd",["false"])[0])
        has_hd = utils.get_bool(params.get("has_hd",["false"])[0])
        return self.timvision_session.get_license_info(contentid, videoType,prefer_hd,has_hd)

    def load_movies(self, params={}):
        begin = int(params.get("begin", ["0"])[0])
        return self.timvision_session.load_all_contents(begin=begin, category="Cinema")

    def load_series(self, params={}):
        begin = int(params.get("begin", ["0"])[0])
        return self.timvision_session.load_all_contents(begin=begin, category="Serie")

    def load_kids(self, params={}):
        begin = int(params.get("begin", ["0"])[0])
        return self.timvision_session.load_all_contents(begin=begin, category="Kids")

    def get_categories(self, params={}):
        return self.timvision_session.get_menu_categories()

    def get_page(self, params):
        page = params.get("page")[0]
        return self.timvision_session.get_page(page)

    def get_contents(self, params):
        url = params.get("url")[0]
        return self.timvision_session.get_contents(url)

    def get_cast(self, params):
        contentId = params.get("contentId")[0]
        return self.timvision_session.getCast(contentId)

    def get_season_trailer(self, params):
        contentId = params.get("contentId")[0]
        return self.timvision_session.getSeasonTrailer(contentId)

    def get_license(self,params,rawdata): #rawdata is widevine payload
        url = urllib.unquote(params.get("license_url")[0])
        return self.timvision_session.get_widevine_response(rawdata,url)
    
    def search(self, params):
        keyword = params.get("keyword",[""])[0]
        return self.timvision_session.search(keyword)

    def set_playing_item(self, params):
        url = params.get("url",[""])[0]
        contentId = params.get("contentId",[""])[0]
        return self.timvision_session.set_playing_media(url, contentId)

    def stop_content(self, params):
        contentId = params.get("contentId")[0]
        time = params.get("time", ["0"])[0]
        return self.timvision_session.stop_content(contentId, time)

    def pause_content(self, params):
        contentId = params.get("contentId")[0]
        time = params.get("time", ["0"])[0]
        return self.timvision_session.pause_consumption(contentId, time)

    def set_content_seen(self, params):
        contentId = params.get("contentId")[0]
        return self.timvision_session.set_seen(contentId)

    def keep_alive(self, params):
        contentId = params.get("contentId")[0]
        return self.timvision_session.keep_alive(contentId)
