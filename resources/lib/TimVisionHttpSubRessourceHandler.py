import urllib
import time
from resources.lib import utils

class TimVisionHttpSubRessourceHandler(object):
    def __init__(self, timvision_session):
        self.timvision_session = timvision_session

    def time_log(self):
        """
            Called by HttpRequestHandler.
            Save the timestamp of the last request received
        """
        self.timvision_session.last_time_request_received = time.time()

    def prefetch_login(self):
        user = utils.get_setting('username')
        passw = utils.get_setting('password')
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

    def get_show_content(self, params):
        content_id = params.get("contentId")[0]
        content_type = params.get("contentType")[0]
        return self.timvision_session.get_show_content(content_id, content_type)

    def get_license_video(self, params):
        content_id = params.get("contentId")[0]
        video_type = params.get("videoType")[0]
        has_hd = utils.get_bool(params.get("has_hd", ["false"])[0])
        return self.timvision_session.get_license_info(content_id, video_type, has_hd)

    def load_all_contents(self, params):
        begin = int(params.get("begin", [0])[0])
        category = params.get("category")[0]
        return self.timvision_session.load_all_contents(begin=begin, category=category)

    def get_categories(self, params={}):
        return self.timvision_session.get_menu_categories()

    def get_page(self, params):
        page = params.get("page")[0]
        return self.timvision_session.get_page(page)

    def get_contents(self, params):
        url = params.get("url")[0]
        return self.timvision_session.get_contents(url)

    def get_cast(self, params):
        content_id = params.get("contentId")[0]
        return self.timvision_session.getCast(content_id)

    def get_season_trailer(self, params):
        content_id = params.get("contentId")[0]
        return self.timvision_session.get_season_trailer(content_id)

    def get_movie_trailer(self, params):
        content_id = params.get("contentId")[0]
        return self.timvision_session.get_movie_trailer(content_id)

    def get_license(self, params, rawdata): #rawdata is widevine payload
        url = urllib.unquote(params.get("license_url")[0])
        return self.timvision_session.get_widevine_response(rawdata, url)

    def search(self, params):
        keyword = params.get("keyword", [""])[0]
        return self.timvision_session.search(keyword)

    def set_playing_item(self, params):
        url = params.get("url", [""])[0]
        content_id = params.get("contentId", [""])[0]
        start_time = float(params.get("time", ["0.0"])[0])
        content_type = params.get("videoType")[0]
        duration = params.get("duration")[0]
        paused =  bool(params.get("paused")[0])
        return self.timvision_session.set_playing_media(url, content_id, start_time, content_type, duration, paused)

    def stop_content(self, params):
        content_id = params.get("contentId")[0]
        stop_time = params.get("time", ["0"])[0]
        threshold = params.get("threshold")[0]
        return self.timvision_session.stop_content(content_id, stop_time, threshold)

    def pause_content(self, params):
        content_id = params.get("contentId")[0]
        pause_time = params.get("time", ["0"])[0]
        threshold = params.get("threshold")[0]
        return self.timvision_session.pause_consumption(content_id, pause_time, threshold)

    def set_content_seen(self, params):
        content_id = params.get("contentId")[0]
        duration = params.get("duration")[0]
        return self.timvision_session.set_seen(content_id, duration)

    def keep_alive(self, params):
        content_id = params.get("contentId")[0]
        return self.timvision_session.keep_alive(content_id)

    def set_favourite(self, params):
        content_id = params.get("contentId")[0]
        value = utils.get_bool(params.get("value")[0])
        mediatype = params.get("mediatype")[0]
        return self.timvision_session.set_favorite(content_id, value, mediatype)

    def get_favourite(self, params):
        return self.timvision_session.get_favourites()

    def is_favourite(self, params):
        content_id = params.get("contentId")[0]
        return self.timvision_session.is_favourite(content_id)

    def get_details(self, params):
        content_id = params.get("contentId")[0]
        return self.timvision_session.get_details(content_id)
