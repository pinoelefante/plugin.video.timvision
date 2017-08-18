import xbmc

class TimVisionHttpSubRessourceHandler:
    """ Represents the callable internal server routes & translates/executes them to requests for Netflix"""

    def __init__ (self, kodi_helper, timvision_session):
        self.kodi_helper = kodi_helper
        self.timvision_session = timvision_session
        self.prefetch_login()

    def prefetch_login(self):
        credentials = self.kodi_helper.get_credentials()
        user = credentials.get('username')
        passw = credentials.get('password')
        if user!='' and passw!='':
            self.timvision_session.login(user, passw)
    
    def login (self, params):
        email = params.get('username', [''])[0]
        password = params.get('password', [''])[0]
        if email != '' and password != '':
            return self.timvision_session.login(email, password)
        return None

    def recommended_video(self, params):
        pageType = params.get('category',[''])[0]
        return self.timvision_session.recommended_video(pageType)
    
    def load_serie_seasons(self, params):
        serieId = params.get('serieId',[''])[0]
        return self.timvision_session.load_serie_seasons(serieId)

    def load_serie_episodes(self, params):
        seasonId = params.get('seasonId',[''])[0]
        return self.timvision_session.load_serie_episodes(seasonId)
    
    def get_license_video(self, params):
        contentid = params.get("contentId",[""])[0]
        videoType = params.get("videoType", [""])[0]
        return self.timvision_session.get_license_info(contentid, videoType)
    def load_movies(self, params={}):
        begin = int(params.get("begin", ["0"])[0])
        load_all = True #bool(params.get("load_all", ["False"])[0])
        return self.timvision_session.load_contents(begin=begin, load_all = load_all, category="Cinema")
    def load_series(self, params={}):
        begin = int(params.get("begin", ["0"])[0])
        load_all = True #bool(params.get("load_all", ["False"])[0])
        return self.timvision_session.load_contents(begin=begin, load_all = load_all, category="Serie")
    def load_kids(self, params={}):
        begin = int(params.get("begin", ["0"])[0])
        load_all = True #bool(params.get("load_all", ["False"])[0])
        return self.timvision_session.load_contents(begin=begin, load_all = load_all, category="Kids")