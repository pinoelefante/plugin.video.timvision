import json
import threading
import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from requests import session, cookies

RECOM_TOP_VIEW = "TOP_VIEWED"
RECOM_MOST_RECENT = "MOST_RECENT"
RECOM_FOR_YOU = "RECOM_FOR_YOU"
RECOM_EXPIRING = "EXPIRING"

class TimVisionSession:
    base_url = 'https://www.timvision.it/AVS'
    deviceType = 'WEB'
    service_name = 'CUBOVISION'
    service_channel = 'CUBOWEB'
    app_version = '10.0.47'
    api_endpoint = session()
    license_endpoint = session()

    def __init__(self):
        self.api_endpoint.headers.update({
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding' : 'gzip, deflate',
        })
        self.license_endpoint.headers.update({
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding' : 'gzip, deflate',
            'Host' : 'license.timvision.it',
            'Origin' : 'https://www.timvision.it'
        })
        #self.plugin_handle = plugin_handle
        self.setup()

    def setup(self):
        return self.load_app_settings() and self.load_app_version()

    def load_app_version(self):
        r = self.api_endpoint.get("https://www.timvision.it/app_ver.js")
        if r.status_code == 200:
            str1 = r.text
            #str1 = str1.rsplit('{')[1].rsplit('}')[0]
            str1 = str1.rsplit('"')[1].rsplit('"')[0]
            self.app_version = str1
            return True
        return False
    def load_app_settings(self):
        url = 'https://www.timvision.it/TIM/'+self.app_version+'/PROD/IT/'+self.service_channel+'/ITALY/PROPERTIES?deviceType='+self.deviceType+'&serviceName='+self.service_name
        r = self.api_endpoint.get(url)
        if r.status_code == 200:
            data = r.json()
            if data['resultCode'] == 'OK':
                self.license_acquisition_url = data['resultObj']['LICENSEACQUISITIONURL']
                self.user_http_header = data['resultObj']['USER_REQ_HEADER_NAME']
                self.widevine_proxy_url = data['resultObj']['WV_PROXY_URL']
                return True
        return False
    def login(self, username, password):
        data = {
            'username':username,
            'password':password,
            'customData':'{"customData":[{"name":"deviceType","value":'+self.deviceType+'},{"name":"deviceVendor","value":""},{"name":"accountDeviceModel","value":""},{"name":"FirmwareVersion","value":""},{"name":"Loader","value":""},{"name":"ResidentApp","value":""},{"name":"DeviceLanguage","value":"it"},{"name":"NetworkType","value":""},{"name":"DisplayDimension","value":""},{"name":"OSversion","value":"Windows 10"},{"name":"AppVersion","value":""},{"name":"DeviceRooted","value":""},{"name":"NetworkOperatoreName","value":""},{"name":"ServiceOperatorName","value":""},{"name":"Custom1","value":"Firefox"},{"name":"Custom2","value":54},{"name":"Custom3","value":"1920x1080"},{"name":"Custom4","value":"PC"},{"name":"Custom5","value":""},{"name":"Custom6","value":""},{"name":"Custom7","value":""},{"name":"Custom8","value":""},{"name":"Custom9","value":""}]}'
        }
        r = self.api_send_request("Login", method = 'POST', postData=data)
        if r[0]:
            self.api_endpoint.headers.__setitem__(self.user_http_header, r[1]["resultObj"])
            self.sessionLoginHash = r[1]["extObject"]["hash"]
            self.avs_cookie = self.api_endpoint.cookies.get("avs_cookie")
            self.license_endpoint.headers.__setitem__('AVS_COOKIE',self.avs_cookie)
            #self.stop_check_session = threading.Event()
            #check_thread = threading.Thread(target=self.check_session, args=(self.stop_check_session))
            #check_thread.start()
            return True
        return False
    def logout(self):
        r = self.api_send_request("Logout")
        if r[0]:
            self.api_endpoint.cookies.clear()
            self.sessionLoginHash = None
            self.api_endpoint.headers.pop(self.user_http_header, None)
            #self.stop_check_session.set()
            return True
        return False
    def is_logged(self):
        return self.sessionLoginHash != None
    def api_url(self, action, others = {}):
        query = ""
        if others!=None:
            for key,value in others:
                query += "&"+key+"="+value
        return self.base_url+"/besc?channel="+self.service_channel+"&providerName=TELECOMITALIA&serviceName="+self.service_name+"&action="+action+"&deviceType="+self.deviceType+query
    def api_send_request(self, action, method = 'GET', queryData=None, postData=None):
        r = None
        if method == "POST":
            r = self.api_endpoint.post(self.api_url(action, queryData), data=postData)
        if method == "GET":
            r = self.api_endpoint.get(self.api_url(action, queryData))
        if method == "OPTIONS":
            r = self.api_endpoint.options(self.api_url(action, queryData))
        if r.status_code == 200:
            data = r.json()
            if data["resultCode"] == "OK":
                return [True, data]
        return [False]

    def recommended_video(self, category):
        url = "https://www.timvision.it/TIM/"+self.app_version+"/PROD_WEB/IT/"+self.service_channel+"/ITALY/TRAY/RECOM?deviceType="+self.deviceType+"&serviceName="+self.service_name
        query = {
            "dataSet":"RICH",
            "orderBy":"year",
            "sortOrder":"desc",
            "area":"HOMEPAGE",
            "category":"HomePage",
            "recomType":category,
            "maxResults":"30"
        }
        r = self.api_endpoint.get(url, params = query)
        if r.status_code == 200:
            data = r.json()
            if data["resultCode"] == "OK":
                return data["resultObj"]["containers"]
        return None
    def load_serie_seasons(self, serieId):
        url = "https://www.timvision.it/TIM/"+self.app_version+"/PROD_WEB/IT/"+self.service_channel+"/ITALY/DETAILS?contentId="+str(serieId)+"&type=SERIES&renderEngine=DELTA&deviceType="+self.deviceType+"&serviceName="+self.service_name
        r = self.api_endpoint.get(url)
        if r.status_code == 200:
            data = r.json()[0]
            if data["resultCode"] == "OK":
                return data["resultObj"]["containers"]
        return None
    def load_serie_episodes(self, seasonId):
        url = "https://www.timvision.it/TIM/"+self.app_version+"/PROD_WEB/IT/"+self.service_channel+"/ITALY/DETAILS?renderEngine=DELTA&deviceType="+self.deviceType+"&serviceName="+self.service_name+"&contentId="+seasonId+"&type=SEASON"
        r = self.api_endpoint.get(url)
        if r.status_code == 200:
            data = r.json()[0]
            if data["resultCode"] == "OK":
                containers = data["resultObj"]["containers"]
                for cont in containers:
                    if cont["layout"] == "SEASON":
                        return cont["items"]
        return None
    def check_session(self, stop_event):
        while not stop_event.is_set():
            self.api_send_request("CheckSession")
            stop_event.wait(600)
        
    def get_license_info(self, contentId, videoType):
        mpdContent = self.get_mpd_file(contentId, videoType)
        if mpdContent != None:
            assetIdWd = self.get_assetIdWd(mpdContent["mpd"])
            return {
                'AVS_COOKIE':self.avs_cookie,
                "mpd_file":mpdContent["mpd"],
                #"cpId":mpdContent["cpId"],
                "widevine_url":self.widevine_proxy_url.replace("{ContentIdAVS}",contentId).replace("{AssetIdWD}",assetIdWd).replace("{CpId}",mpdContent["cpId"]).replace("{Type}","VOD").replace("{ClientTime}",str(long(time.time()*1000))).replace("{Channel}",self.service_channel).replace("{DeviceType}","CHROME").replace('http://', 'https://')
            }
        return None
    def get_assetIdWd(self, mpdUrl):
        partial = mpdUrl[mpdUrl.find("DASH")+5:]
        partial = partial[0:partial.find("/")]
        return partial
    def get_mpd_file(self,contentId,videoType):
        url = "https://www.timvision.it/TIM/"+self.app_version+"/PROD_WEB/IT/"+self.service_channel+"/ITALY/PLAY?contentId="+contentId+"&deviceType=CHROME&serviceName="+self.service_name+"&type="+videoType
        r = self.api_endpoint.get(url)
        if r.status_code == 200:
            data = r.json()
            cpId = data["resultObj"]["cp_id"]
            mpd = data["resultObj"]["src"]
            return {"cpId": cpId, "mpd":mpd}
        return None
    def load_movies(self, begin=0, progress=100):
        end = int(begin)+progress
        url = "https://www.timvision.it/TIM/"+self.app_version+"/PROD_WEB/IT/"+self.service_channel+"/ITALY/TRAY/SEARCH/VOD?from="+str(begin)+"&to="+str(end)+"&sorting=order:year+desc&categoryName=Cinema&offerType=SVOD&deviceType="+self.deviceType+"&serviceName="+self.service_name
        r = self.api_endpoint.get(url)
        if r.status_code == 200:
            data = r.json()
            if data["resultCode"] == "OK":
                maxCount = data["resultObj"]["total"]
                movies = data["resultObj"]["containers"]
                if xbmcplugin.getSetting(int(sys(argv[1])), "film_load_all"):
                    if end<=maxCount:
                        other_movie = self.load_movies(end)
                        if other_movie!=None:
                            movies.extend(other_movie)
                return movies
        return None