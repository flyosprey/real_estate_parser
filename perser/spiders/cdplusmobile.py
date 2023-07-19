from typing import Tuple
import re
import urllib.parse
import scrapy
from scrapy.cmdline import execute
from scrapy_splash import SplashRequest

from perser.spiders import init_file
from perser.spiders.config import PermitNumbers
from perser import utils


class CdplusmobileSpider(scrapy.Spider):
    name = "cdplusmobile"
    allowed_domains = ["cdplusmobile.marioncountyfl.org"]
    start_url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll"

    # blacklisted_proxy = ["34.140.70.242:8080", "5.189.184.6:80", "77.247.108.17:33080", "157.245.27.9:3128",
    #                      "64.225.8.135:9995", "168.119.14.45:3128", "129.159.112.251:3128", "41.65.174.98:1976",
    #                      "129.153.157.63:3128", "51.159.115.233:3128"]

    blacklisted_proxy = ["77.247.108.17:33080", "157.245.27.9:3128", "88.99.234.110:2021", "8.209.114.72:3129"]

    def __init__(self, *args, **kwargs):
        self._proxy_https = utils.get_proxy(blacklist=self.blacklisted_proxy, is_https=True)

        self._headers_behavior = init_file.HeadersBehavior()

        self._session_id, self._track_id, self._window_id, self._main_page = "", "", "", ""
        self._previous_page_callback, self._previous_page = "", ""

        self._visited_pages, self._visited_button_pages, self._processed_permits = set(), set(), set()
        self._button_pages_to_visit = []
        self._data = {}
        self._duple_page = 0

        self.__lua_script = '''
                            function main(splash, args)
                                splash.js_enabled = true
                                assert(splash:go(args.url))
                                assert(splash:wait(30))
                                return {
                                    html = splash:html(),
                                }
                            end
                        '''

        super().__init__(*args, **kwargs)

    def start_requests(self):
        general_headers = self._headers_behavior.get_base_headers()
        callback_headers = self._headers_behavior.get_callback_headers(base_headers=general_headers)
        permit_number = str(PermitNumbers.pop(0))
        self._data[permit_number] = {}
        splash_args = {'lua_source': self.__lua_script, 'wait': 30, 'proxy': self._proxy_https}
        # yield scrapy.Request(
        #     method="GET", url=self.start_url, callback=self.parse, dont_filter=True,
        #     meta={
        #         'proxy': self._proxy_https,
        #         "data": {
        #                 "permit_number": permit_number, "general_headers": general_headers,
        #                 "callback_headers": callback_headers
        #             },
        #     }
        # )
        yield SplashRequest(url=self.start_url, callback=self.parse, method="GET", args=splash_args,
                            splash_headers=general_headers, dont_filter=True,
                            cb_kwargs={
                                "data": {
                                    "permit_number": permit_number, "general_headers": general_headers,
                                    "callback_headers": callback_headers
                                }
                            })

    def parse(self, response, **kwargs):
        selector = scrapy.Selector(text=response.text)

        session_id = selector.xpath(".//input[@name='IW_SessionID_']//@value").get()
        track_id = selector.xpath(".//input[@name='IW_TrackID_']//@value").get()
        window_id = selector.xpath(".//input[@name='IW_WindowID_']//@value").get()

        payload = f'IW_SessionID_={session_id}&IW_TrackID_={track_id}&IW_WindowID_={window_id}&' \
                  'IW_dpr=1&IW_width=0&IW_height=0'
        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/" \
              "webpermitnew/webpermits.dll/" + session_id

        yield scrapy.Request(
            method="POST", url=url, callback=self.main_page, dont_filter=True,
            body=payload, headers=kwargs["data"]["callback_headers"],
            meta={
                'proxy': self._proxy_https,
                "data": {**kwargs["data"], "session_id": session_id, "track_id": track_id, "window_id": window_id}
            }
        )

    def main_page(self, response):
        html = self.normalize_html(html=response.text)
        form_data = self.get_form_data(selector=scrapy.Selector(text=html), callback_name="By Permit")

        meta_data = response.meta["data"]
        payload = f'{form_data["callback_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["callback_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={meta_data["session_id"]}&' \
                  f'IW_TrackID_={meta_data["track_id"]}&IW_WindowID_={meta_data["window_id"]}'

        url = f'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncClick&x=292&y=34&' \
              f'which=0&modifiers='

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback, dont_filter=True,
            body=payload, headers=meta_data["callback_headers"],
            meta={
                'proxy': self._proxy_https,
                "data": {**meta_data, "callback_func": self.search_by_permit_number}
            }
        )

    def search_by_permit_number(self, response):
        html = self.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        form_data = self.get_form_data(selector=selector, callback_name="PERMIT")
        self._previous_page_callback = selector.xpath(".//input[@title='Go Back']//@name").get()
        if not self._previous_page_callback:
            raise Exception("Failed to extract _previous_page_callback")

        meta_data = response.meta["data"]
        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll' \
              f'/{meta_data["session_id"]}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncKeyUp&' \
              'which=39&char=%27&modifiers='
        payload = f'EDTPERMITNBR={meta_data["permit_number"]}&IW_FormName={form_data["form_name"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}&IW_FormClass={form_data["form_class"]}&' \
                  f'IW_Action={form_data["callback_method"]}&IW_ActionParam=&' \
                  f'IW_Offset=&IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}'

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': self._proxy_https, "data": {**meta_data, "callback_func": self.search_by_permit_login}}
        )

    def search_by_permit_login(self, response):
        html = self.normalize_html(html=response.text)
        form_data = self.get_form_data(selector=scrapy.Selector(text=html), callback_name="Continue")

        meta_data = response.meta["data"]

        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncClick&x=166&y=18&' \
              'which=0&modifiers='
        payload = f'EDTPERMITNBR={meta_data["permit_number"]}&{form_data["callback_method"]}=&' \
                  f'IW_FormName={form_data["form_name"]}&IW_FormClass={form_data["form_class"]}&' \
                  f'IW_Action={form_data["callback_method"]}&IW_ActionParam=&IW_Offset=&' \
                  f'IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}'

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': self._proxy_https,"data": {**meta_data, "callback_func": self.permit_details}},
        )

    def permit_details(self, response):
        self.logger.info(msg="Passed login")
        html = self.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        meta_data = response.meta["data"]

        permit_number = meta_data["permit_number"]
        self._data[permit_number]["permit_details"] = {}
        for _id in range(1, len(selector.xpath(".//span[contains(@id, 'IWLABEL')]")) + 1):
            self._data[permit_number]["permit_details"].update(self.get_detail_info(selector=selector, id_value=_id))

        self._button_pages_to_visit = selector.xpath(".//div[@id='RGNBUTTON']//input/@value").getall()
        self._main_page = selector.xpath(".//span[@id='LBLPAGEID']//text()").get()

        callback = selector.xpath(".//div[@id='RGNBUTTON']//input/@value").get()
        form_data = self.get_form_data(selector=selector, callback_name=callback)

        url, payload = self.pagination_url_payload(form_data=form_data, meta_data=meta_data)

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=response.meta["data"]["callback_headers"], dont_filter=True,
            meta={'proxy': self._proxy_https, "data": {**meta_data, "callback_func": self.collect_page}}
        )

    def collect_page(self, response):
        html = self.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        if not selector.xpath(".//input[contains(@id, 'GUESTLOGIN')]"):
            current_page = selector.xpath(".//span[@id='LBLPAGEID']//text()").get()
            self.logger.info(msg=f"Visit: '{current_page}'")
            self._duple_page = self._duple_page + 1 if current_page == self._previous_page else 0
            meta_data = response.meta["data"]
            permit_number = meta_data["permit_number"]

            button_pages = self.get_button_pages(selector=selector, current_page=current_page)

            callback = self._previous_page_callback
            if self._main_page == current_page or (current_page not in self._visited_pages and button_pages):
                for button_page in button_pages:
                    if button_page not in self._visited_button_pages:
                        self._button_pages_to_visit += button_pages
                if self._button_pages_to_visit:
                    callback = self._button_pages_to_visit.pop(-1)
            elif self._duple_page == 0:
                if not selector.xpath(".//input[contains(@id, 'GUESTLOGIN')]"):
                    key_name = self._normalize_key(key=current_page)
                    self._data[permit_number][key_name] = self.get_page_data(selector=selector)
                    self.logger.info(msg=f"Extracted data: '{current_page}'")

            self._visited_pages.add(current_page)
            if not self._button_pages_to_visit and permit_number not in self._processed_permits:
                self._processed_permits.add(permit_number)
                if len(self._processed_permits) == 2:
                    yield self._data

            if selector.xpath(".//input[contains(@id, 'GUESTLOGIN')]"):
                if PermitNumbers:
                    response.meta["data"]["permit_number"] = PermitNumbers.pop(0)
                    yield self.search_by_permit_number(response=response)

            self._previous_page = current_page

            form_data = self.get_form_data(selector=selector, callback_name=callback)
            meta_data = response.meta["data"]
            if self._duple_page >= 3:
                url, payload = self._open_previous_page(html=html, callback=callback, form_data=form_data,
                                                        meta_data=meta_data)
                yield scrapy.Request(
                    method="POST", url=url, callback=self.collect_page, dont_filter=True,
                    body=payload, headers=meta_data["callback_headers"],
                    meta={'proxy': self._proxy_https, "data": meta_data}
                )
            else:
                url, payload = self.pagination_url_payload(form_data=form_data, meta_data=meta_data)
                yield scrapy.Request(
                    method="POST", url=url, callback=self.site_callback,
                    body=payload, headers=meta_data["callback_headers"], dont_filter=True,
                    meta={'proxy': self._proxy_https, "data": {**meta_data, "callback_func": self.collect_page}}
                )

    def get_button_pages(self, selector: scrapy.Selector, current_page: str) -> list:
        button_pages = []
        if current_page != self._main_page:
            button_pages = set(selector.xpath(".//div[@id='RGNBUTTON']//input[not(@disabled)]//@value").getall())

        return button_pages

    def _open_previous_page(self, html: str, callback: str, form_data: dict, meta_data: dict) -> Tuple[str, str]:
        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/" \
              f"{meta_data['session_id']}/"
        msgdlgok = re.search(r"var MSGDLGOKIsVisible = (.+?);", html)
        cogrid = re.search(r"FindElem\('COGRID'\)\.value=\"(.+?)\"", html)[1]
        if msgdlgok and cogrid:
            msgdlgok = msgdlgok[1]
            cogrid = urllib.parse.quote(cogrid[1])
            payload = f'MSGDLGOK=%5Eisvisible%3A{msgdlgok}&COGRID={cogrid}&IW_FormName={form_data["form_name"]}&' \
                      f'IW_FormClass={form_data["form_class"]}&IW_Action={callback}&IW_ActionParam=&' \
                      f'IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                      f'IW_WindowID_={meta_data["window_id"]}'

            return url, payload

        self.logger.info("Cannot extract msgdlgok or cogrid | Second type of request for 'BACK' button")
        raise Exception("Cannot extract msgdlgok or cogrid | Second type of request for 'BACK' button")

    def get_page_data(self, selector: scrapy.Selector) -> list:
        columns = selector.xpath(".//table[contains(@id, 'div0')]//"
                                 "table[contains(@id, 'ID_')]//span[contains(@id, 'T')]/text()").getall()
        result = []
        if columns:
            columns = [column.replace(" ", "_").lower() for column in columns]
            rows = selector.xpath(".//tr[contains(@id, 'row')]")
            for row in rows:
                normalize_rows = {}
                for index, item in enumerate(row.xpath(".//div[contains(@class, 'nowrapc')]//text()").getall()):
                    if not item.strip():
                        break
                    normalize_rows.update({columns[index]: item})
                if normalize_rows:
                    result.append(normalize_rows)

        for id_value in range(1, len(selector.xpath("//span[contains(@id, 'LABEL')]").getall()) + 1):
            result.append(self.get_detail_info(selector=selector, id_value=id_value))

        return result

    def site_callback(self, response):
        meta_data = response.meta["data"]
        session_id, track_id, window_id = meta_data["session_id"], meta_data["track_id"], meta_data["window_id"]

        session_id_match = re.search(r"IW_SessionID_\": \"(.+?)\"", response.text)
        meta_data["session_id"] = session_id_match[1] if session_id_match else session_id

        track_id_match = re.search(r"<trackid>(.*?)</trackid>", response.text)
        track_id_match = re.search(r"IW_TrackID_\": (.+?)}", response.text) if not track_id_match else track_id_match
        meta_data["track_id"] = track_id_match[1].strip() if track_id_match else track_id

        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/" \
              f"{meta_data['session_id']}/"
        payload = f'IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}'

        yield scrapy.Request(
            method="POST", url=url, callback=meta_data['callback_func'],
            body=payload, headers=meta_data["general_headers"], dont_filter=True,
            meta={'proxy': self._proxy_https, "data": meta_data}
        )

    def _generate_key_for_data(self, current_page: str) -> str:
        page_words = current_page.split()
        key_name = ""
        for word in page_words:
            key_name = f"{key_name}_{word.lower()}".strip("_")
            if not self._data.get(word):
                break

        return key_name

    def pagination_url_payload(self, form_data: dict, meta_data: dict) -> Tuple[str, str]:
        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncClick&x=166&y=18&' \
              f'which=0&modifiers='
        payload = f'{form_data["callback_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["callback_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}'

        return url, payload

    def get_detail_info(self, selector: scrapy.Selector, id_value: int) -> dict:
        value = selector.xpath(f".//input[@id='IWDBEDIT{id_value}']//@value").get()
        value = selector.xpath(f".//textarea[@id='IWDBTEXT{id_value}']//text()").get() if not value else value
        label = selector.xpath(f".//span[@id='IWLABEL{id_value}']//text()").get()
        if label and value is not None:
            label = self._normalize_key(key=label)

            return {label: value.strip()}
        elif not label and not value:
            return {}

        self.logger.error(msg=f"Failed to extract data of 'IWDBEDIT{id_value}'")
        raise Exception("Failed to extract data of 'IWDBEDIT%s' ", id_value)

    @staticmethod
    def _normalize_key(key: str) -> str:
        key = re.sub(r"[#:]", "", key)
        key = " ".join(key.split()).replace(" ", "_").lower()

        return key

    def get_form_data(self, selector: scrapy.Selector, callback_name: str) -> dict:
        form_name = selector.xpath(".//input[@name='IW_FormName']//@value").get()
        form_class = selector.xpath(".//input[@name='IW_FormClass']//@value").get()

        callback_method = selector.xpath(f".//input[contains(@value, '{callback_name}')]//@name").get()
        if not callback_method:
            callback_method = selector.xpath(f".//input[@name='{callback_name}']//@id").get()
        if not callback_method:
            callback_method = selector.xpath(f".//span[contains(@id, '{callback_name}')]//@name").get()

        if callback_method or form_class or form_name:
            return {"form_name": form_name, "form_class": form_class, "callback_method": callback_method}

        self.logger.error(msg="Failed to get form_data")
        raise Exception("Failed to get form_data")

    @staticmethod
    def normalize_html(html: str) -> str:
        bad_tags = re.findall(r"</?[A-Z]+?[\s>]|[A-Z]+?=\"", html)
        if bad_tags:
            bad_tags = set(bad_tags)
            for bad_tag in bad_tags:
                html = html.replace(bad_tag, bad_tag.lower())

        return html


if __name__ == "__main__":
    execute()
