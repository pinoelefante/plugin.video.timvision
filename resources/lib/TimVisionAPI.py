import json
import threading
import time
import urllib
import os
from requests import session, cookies


class TimVisionSession:
    BASE_URL_TIM = ""
    BASE_URL_AVS = "https://www.timvision.it/AVS"
    deviceType = 'WEB'
    service_name = 'CUBOVISION'
    service_channel = 'CUBOWEB'
    providerName = "TELECOMITALIA"
    app_version = '10.0.47'
    api_endpoint = session()
    license_endpoint = session()
    user_http_header = "X-Avs-Username"
    sessionLoginHash = None
    widevine_proxy_url = "https://license.cubovision.it/WidevineManager/WidevineManager.svc/GetLicense/{ContentIdAVS}/{AssetIdWD}/{CpId}/{Type}/{ClientTime}/{Channel}/{DeviceType}"

    def __init__(self):
        self.api_endpoint.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding': 'gzip, deflate',
        })
        self.license_endpoint.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'license.timvision.it',
            'Origin': 'https://www.timvision.it'
        })
        self.setup()

    def setup(self):
        return self.load_app_version() and self.load_app_settings()

    def load_app_version(self):
        r = self.api_endpoint.get("https://www.timvision.it/app_ver.js")
        if r.status_code == 200:
            version = r.text.rsplit('"')[1].rsplit('"')[0]
            self.app_version = version
            self.BASE_URL_TIM = "https://www.timvision.it/TIM/{appVersion}/PROD_WEB/IT/{channel}/ITALY"
            return True
        return False

    def load_app_settings(self):
        url = "/PROPERTIES?deviceType={deviceType}&serviceName={serviceName}"
        data = self.send_request(url,baseUrl=self.BASE_URL_TIM)
        if data != None:
            self.license_acquisition_url = data['resultObj']['LICENSEACQUISITIONURL']
            self.user_http_header = data['resultObj']['USER_REQ_HEADER_NAME']
            self.widevine_proxy_url = data['resultObj']['WV_PROXY_URL']
            return True
        return False

    def login(self, username, password):
        data = {
            'username': username,
            'password': password,
            'customData': '{"customData":[{"name":"deviceType","value":' + self.deviceType + '},{"name":"deviceVendor","value":""},{"name":"accountDeviceModel","value":""},{"name":"FirmwareVersion","value":""},{"name":"Loader","value":""},{"name":"ResidentApp","value":""},{"name":"DeviceLanguage","value":"it"},{"name":"NetworkType","value":""},{"name":"DisplayDimension","value":""},{"name":"OSversion","value":"Windows 10"},{"name":"AppVersion","value":""},{"name":"DeviceRooted","value":""},{"name":"NetworkOperatoreName","value":""},{"name":"ServiceOperatorName","value":""},{"name":"Custom1","value":"Firefox"},{"name":"Custom2","value":54},{"name":"Custom3","value":"1920x1080"},{"name":"Custom4","value":"PC"},{"name":"Custom5","value":""},{"name":"Custom6","value":""},{"name":"Custom7","value":""},{"name":"Custom8","value":""},{"name":"Custom9","value":""}]}'
        }
        url = "/besc?action=Login&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        r = self.send_request(
            url=url, baseUrl=self.BASE_URL_AVS, method="POST", data=data)
        if r != None:
            self.api_endpoint.headers.__setitem__(
                self.user_http_header, r["resultObj"])
            self.sessionLoginHash = r["extObject"]["hash"]
            avs_cookie = self.api_endpoint.cookies.get("avs_cookie")
            self.license_endpoint.headers.__setitem__(
                'AVS_COOKIE', avs_cookie)
            self.stop_check_session = threading.Event()
            check_thread = threading.Thread(target=self.check_session)
            check_thread.start()
            return True
        return False

    def logout(self):
        url = "/besc?action=Logout&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        r = self.send_request(url, baseUrl=self.BASE_URL_AVS)
        if r != None:
            self.api_endpoint.cookies.clear()
            self.sessionLoginHash = None
            self.api_endpoint.headers.pop(self.user_http_header, None)
            self.stop_check_session.set()
            return True
        return False

    def is_logged(self):
        return self.sessionLoginHash != None

    def __compile_url(self, url):
        return url.replace("{appVersion}", self.app_version).replace("{channel}", self.service_channel).replace("{serviceName}", self.service_name).replace("{deviceType}", self.deviceType).replace("{providerName}", self.providerName)

    def send_request(self, url, baseUrl, method="GET", data={}):
        if not url.startswith("https://"):
            url = baseUrl + url
        url = self.__compile_url(url)
        self.log_myfile("Sending "+method+" request to "+url)
        r = self.api_endpoint.get(url, params=data) if method == "GET" else self.api_endpoint.post(url, data=data)
        self.log_myfile("Status Code: "+str(r.status_code))
        if r.status_code == 200:
            data = r.json()
            self.log_myfile(msg=("Content: "+r.text))
            if isinstance(data, list):
                self.log_myfile("JSON result is an array")
                data = data[0]
            if data["resultCode"] == "OK":
                return data
        return None

    def load_serie_seasons(self, serieId):
        url = "/DETAILS?contentId="+str(serieId)+"&type=SERIES&renderEngine=DELTA&deviceType={deviceType}&serviceName={serviceName}"
        return self.get_contents(url)

    def load_serie_episodes(self, seasonId):
        url = "/DETAILS?renderEngine=DELTA&contentId="+seasonId+"&type=SEASON&deviceType={deviceType}&serviceName={serviceName}"
        data = self.get_contents(url)
        if data != None:
            for cont in data:
                if cont["layout"] == "SEASON":
                    return cont["items"]
        return None

    def check_session(self):
        url = "/besc?action=CheckSession&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        while not self.stop_check_session.is_set():
            r = self.send_request(url=url, baseUrl=self.BASE_URL_AVS)
            if r != None:
                if r["resultObj"]["sessionFlag"] == "N":
                    self.logout()
            self.stop_check_session.wait(600)

    def get_license_info(self, contentId, videoType, prefer_hd=False, has_hd=False):
        mpdContent = self.get_mpd_file(contentId, videoType)
        if mpdContent != None:
            assetIdWd = self.get_assetIdWd(mpdContent["mpd"])
            if has_hd and prefer_hd:
                mpdContent["mpd"]=mpdContent["mpd"].replace("_SD.mpd","_HD.mpd")
            return {
                "mpd_file": mpdContent["mpd"],
                "widevine_url": self.widevine_proxy_url.replace("{ContentIdAVS}", contentId).replace("{AssetIdWD}", assetIdWd).replace("{CpId}", mpdContent["cpId"]).replace("{Type}", "VOD").replace("{ClientTime}", str(long(time.time() * 1000))).replace("{Channel}", self.service_channel).replace("{DeviceType}", "CHROME").replace('http://', 'https://')
            }
        return None

    def get_assetIdWd(self, mpdUrl):
        partial = mpdUrl[mpdUrl.find("DASH") + 5:]
        partial = partial[0:partial.find("/")]
        return partial

    def get_mpd_file(self, contentId, videoType):
        url = "/PLAY?contentId="+contentId+"&deviceType=CHROME&serviceName={serviceName}&type="+videoType
        data = self.send_request(url, baseUrl=self.BASE_URL_TIM)
        if data != None:
            cpId = data["resultObj"]["cp_id"]
            mpd = data["resultObj"]["src"]
            return {"cpId": cpId, "mpd": mpd}
        return None

    def load_all_contents(self, category, begin=0, progress=49):
        end = int(begin) + progress
        url = "/TRAY/SEARCH/VOD?from="+str(begin)+"&to="+str(end)+"&sorting=order:title+asc&categoryName="+category+"&offerType=SVOD&deviceType={deviceType}&serviceName={serviceName}"
        data = self.send_request(url, baseUrl=self.BASE_URL_TIM)
        if data != None:
            maxCount = data["resultObj"]["total"]
            movies = data["resultObj"]["containers"]
            if end <= maxCount:
                other_movie = self.load_all_contents(
                    begin=end, category=category)
                if other_movie != None:
                    movies.extend(other_movie)
            return movies
        return None

    def get_menu_categories(self):
        url = "/menu?deviceType={deviceType}&serviceName={serviceName}"
        return self.get_contents(url)

    def get_page(self, page):
        url = "/PAGE/"+page+"?deviceType={deviceType}&serviceName={serviceName}"
        return self.get_contents(url)

    def get_contents(self, url, data={}):
        data = self.send_request(url,baseUrl=self.BASE_URL_TIM, data=data)
        if data != None:
            return data["resultObj"]["containers"]
        return None

    def log_myfile(self, msg,filename="timvision.log",enable=False):
        if enable:
            if(msg != None):
                if isinstance(msg, unicode):
                    msg = msg.encode('utf-8')
                desktop = os.path.join(os.environ["HOMEPATH"], "Desktop")
                filepath = os.path.join(desktop, filename)
                f = open(filepath, "a")
                f.writelines(msg + "\n")
                f.close()

    def get_widevine_response(self, widevineRequest, widevine_url, count=0):
        if count == 3:
            return None
        self.log_myfile("Trying to get widevine license", filename="widevine.log")
        resp = self.license_endpoint.post(widevine_url, data=widevineRequest)
        self.log_myfile("Status code: "+str(resp.status_code), filename="widevine.log")
        self.log_myfile("widevine license")
        if resp.status_code == 200:
            self.log_myfile("We get it! WOW", filename="widevine.log")
            return resp.content
        else:
            return self.get_widevine_response(widevineRequest,widevine_url, count+1)
