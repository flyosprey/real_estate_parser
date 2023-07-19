from typing import Tuple
import re
import urllib.parse
import scrapy
from scrapy.cmdline import execute

from perser.spiders import init_file
from perser.spiders.config import PermitNumbers
from perser import utils



class CdplusmobileSpider(scrapy.Spider):
    name = "cdplusmobile"
    allowed_domains = ["cdplusmobile.marioncountyfl.org"]
    start_url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll"

    blacklisted_proxy = ["34.140.70.242:8080", "5.189.184.6:80", "77.247.108.17:33080", "157.245.27.9:3128",
                         "64.225.8.135:9995", "168.119.14.45:3128", "129.159.112.251:3128", "41.65.174.98:1976",
                         "129.153.157.63:3128", "51.159.115.233:3128"]

    def __init__(self, *args, **kwargs):
        self._proxy_https = utils.get_proxy(blacklist=self.blacklisted_proxy, is_https=True)

        headers_behavior = init_file.HeadersBehavior()
        self._general_headers = headers_behavior.get_base_headers()
        self._callback_headers = headers_behavior.get_callback_headers()

        self._referer = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/%s/"
        self._session_id, self._track_id, self._window_id, self._main_page = "", "", "", ""
        self._previous_page_callback, self._previous_page = "", ""

        self._button_pages_to_visit = []
        self._visited_pages, self._visited_button_pages = set(), set()
        self._data = {"permit_details": {}}

        self._duple_page = 0

        super().__init__(*args, **kwargs)

    def start_requests(self):
        for permit_number in PermitNumbers:
            yield scrapy.Request(
                method="GET", url=self.start_url, callback=self.parse, headers=self._general_headers,
                meta={
                    'proxy': self._proxy_https,
                    "data": {"permit_number": permit_number}
                }
            )

    def parse(self, response, **kwargs):
        selector = scrapy.Selector(text=response.text)

        self._session_id = selector.xpath(".//input[@name='IW_SessionID_']//@value").get()
        self._track_id = selector.xpath(".//input[@name='IW_TrackID_']//@value").get()
        self._window_id = selector.xpath(".//input[@name='IW_WindowID_']//@value").get()

        self._callback_headers["Referer"] = self._referer % self._session_id
        payload = f'IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}&IW_WindowID_={self._window_id}'
        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/" \
              "webpermitnew/webpermits.dll/" + self._session_id

        yield scrapy.Request(
            method="POST", url=url, callback=self.main_page,
            body=payload, headers=self._callback_headers,
            meta={
                'proxy': self._proxy_https,
                "data": {"permit_number": response.meta["data"]["permit_number"]}
            }
        )

    def main_page(self, response):
        html = self.normalize_html(html=response.text)
        form_data = self.get_form_data(selector=scrapy.Selector(text=html), callback_name="By Permit")

        payload = f'{form_data["callback_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["callback_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}&' \
                  f'IW_WindowID_={self._window_id}'

        url = f'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{self._session_id}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncClick&x=292&y=34&' \
              f'which=0&modifiers='

        self._callback_headers["Referer"] = self._referer % self._session_id

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=self._callback_headers,
            meta={
                'proxy': self._proxy_https,
                "data": {
                    "permit_number": response.meta["data"]["permit_number"],
                    "callback_func": self.search_by_permit_number
                }
            }
        )

    def search_by_permit_number(self, response):
        html = self.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        form_data = self.get_form_data(selector=selector, callback_name="PERMIT")
        self._previous_page_callback = selector.xpath(".//input[@title='Go Back']//@name").get()
        if not self._previous_page_callback:
            raise Exception("Failed to extract _previous_page_callback")

        permit_number = response.meta["permit_number"]
        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll' \
              f'/{self._session_id}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncKeyUp&' \
              'which=39&char=%27&modifiers='
        payload = f'EDTPERMITNBR={permit_number}&IW_FormName={form_data["form_name"]}&' \
                  f'IW_WindowID_={self._window_id}&IW_FormClass={form_data["form_class"]}&' \
                  f'IW_Action={form_data["callback_method"]}&IW_ActionParam=&' \
                  f'IW_Offset=&IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}'

        self._callback_headers["Referer"] = self._referer % self._session_id

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=self._callback_headers,
            meta={
                'proxy': self._proxy_https,
                "callback_func": self.search_by_permit_login,
                "permit_number": permit_number
            }
        )

    def search_by_permit_login(self, response):
        html = self.normalize_html(html=response.text)
        form_data = self.get_form_data(selector=scrapy.Selector(text=html), callback_name="Continue")

        permit_number = response.meta["permit_number"]

        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{self._session_id}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncClick&x=166&y=18&' \
              f'which=0&modifiers='
        payload = f'EDTPERMITNBR={permit_number}&{form_data["callback_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}&IW_Action={form_data["callback_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}&' \
                  f'IW_WindowID_={self._window_id}'

        self._callback_headers["Referer"] = self._referer % self._session_id

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=self._callback_headers,
            meta={
                'proxy': self._proxy_https,
                "data": {
                    "permit_number": permit_number,
                    "callback_func": self.permit_details
                }
            },
        )

    def permit_details(self, response):
        self.logger.info(msg="Passed login")
        html = self.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        permit_number = response.meta["data"]["permit_number"]

        self._data[permit_number]["permit_details"] = {}
        for _id in range(1, len(selector.xpath(".//span[contains(@id, 'IWLABEL')]"))+1):
            self._data[permit_number]["permit_details"].update(self.get_detail_info(selector=selector, id_value=_id))

        self._button_pages_to_visit = selector.xpath(".//div[@id='RGNBUTTON']//input/@value").getall()
        self._main_page = selector.xpath(".//span[@id='LBLPAGEID']//text()").get()

        callback = selector.xpath(".//div[@id='RGNBUTTON']//input/@value").get()
        form_data = self.get_form_data(selector=selector, callback_name=callback)

        url, payload = self.pagination_url_payload(form_data=form_data)

        yield scrapy.Request(
            method="POST", url=url, callback=self.site_callback,
            body=payload, headers=self._callback_headers,
            meta={
                'proxy': self._proxy_https,
                "data": {
                    "permit_number": permit_number,
                    "callback_func": self.collect_page
                }
            }
        )

    def collect_page(self, response):
        html = self.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        current_page = selector.xpath(".//span[@id='LBLPAGEID']//text()").get()
        self.logger.info(msg=f"Visit: '{current_page}'")
        self._duple_page = self._duple_page + 1 if current_page == self._previous_page else 0
        permit_number = response.meta["data"]["permit_number"]

        button_pages = []
        if current_page != self._main_page:
            button_pages = set(selector.xpath(".//div[@id='RGNBUTTON']//input[not(@disabled)]//@value").getall())

        callback = self._previous_page_callback
        if self._main_page == current_page or (current_page not in self._visited_pages and button_pages):
            for button_page in button_pages:
                if button_page not in self._visited_button_pages:
                    self._button_pages_to_visit += button_pages
            callback = self._button_pages_to_visit.pop(-1)
        elif self._duple_page == 0:  # TODO NEED TO CHECK!
            key_name = self._generate_key_for_data(current_page=current_page)
            self._data[permit_number][key_name] = self.get_page_data(selector=selector)
            self.logger.info(msg=f"Extracted data: '{current_page}'")

        self._visited_pages.add(current_page)
        if not self._button_pages_to_visit:
            yield self._data

        self._previous_page = current_page

        form_data = self.get_form_data(selector=selector, callback_name=callback)
        if self._duple_page >= 3:
            url, payload = self._open_previous_page(html=html, callback=callback, form_data=form_data)
            yield scrapy.Request(
                method="POST", url=url, callback=self.collect_page, dont_filter=True,
                body=payload, headers=self._callback_headers,
                meta={
                    'proxy': self._proxy_https,
                    "data": {
                        "permit_number": permit_number,
                        "callback_func": self.collect_page
                    }
                }
            )
        else:
            url, payload = self.pagination_url_payload(form_data=form_data)
            yield scrapy.Request(
                method="POST", url=url, callback=self.site_callback,
                body=payload, headers=self._callback_headers, dont_filter=True,
                meta={
                    'proxy': self._proxy_https,
                    "data": {
                        "permit_number": response.meta["data"]["permit_number"],
                        "callback_func": self.collect_page
                    }
                },
            )

    def _open_previous_page(self, html: str, callback: str, form_data: dict) -> Tuple[str, str]:
        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/" \
              f"{self._session_id}/"
        msgdlgok = re.search(r"var MSGDLGOKIsVisible = (.+?);", html)
        cogrid = re.search(r"FindElem\('COGRID'\)\.value=\"(.+?)\"", html)[1]
        if msgdlgok and cogrid:
            msgdlgok = msgdlgok[1]
            cogrid = urllib.parse.quote(cogrid[1])
            payload = f'MSGDLGOK=%5Eisvisible%3A{msgdlgok}&COGRID={cogrid}&IW_FormName={form_data["form_name"]}&' \
                      f'IW_FormClass={form_data["form_class"]}&IW_Action={callback}&IW_ActionParam=&' \
                      f'IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}&IW_WindowID_={self._window_id}'

            return url, payload

        self.logger.info("Cannot extract msgdlgok or cogrid | Second type of request for 'BACK' button")
        raise Exception("Cannot extract msgdlgok or cogrid | Second type of request for 'BACK' button")

    def get_page_data(self, selector: scrapy.Selector):
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

        for id_value in range(1, len(selector.xpath("//span[contains(@id, 'LABEL')]").getall())+1):
            result.append(self.get_detail_info(selector=selector, id_value=id_value))

        return result

    def site_callback(self, response):
        session_id = re.search(r"IW_SessionID_\": \"(.+?)\"", response.text)
        self._session_id = session_id[1] if session_id else self._session_id

        track_id = re.search(r"<trackid>(.*?)</trackid>", response.text)
        track_id = re.search(r"IW_TrackID_\": (.+?)}", response.text) if not track_id else track_id
        self._track_id = track_id[1].strip() if track_id else self._track_id

        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/" \
              f"{self._session_id}/"
        payload = f'IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}'

        yield scrapy.Request(
            method="POST", url=url, callback=response.meta["data"]['callback_func'],
            body=payload, headers=self._general_headers, dont_filter=True,
            meta={
                'proxy': self._proxy_https,
                "data": {
                    "permit_number": response.meta["data"]["permit_number"],
                }
            },
        )

    def _generate_key_for_data(self, current_page: str) -> str:
        page_words = current_page.split()
        key_name = ""
        for word in page_words:
            key_name = f"{key_name}_{word.lower()}".strip("_")
            if not self._data.get(word):
                break

        return key_name

    def pagination_url_payload(self, form_data: dict) -> Tuple[str, str]:
        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{self._session_id}/$/callback?callback={form_data["callback_method"]}.DoOnAsyncClick&x=166&y=18&' \
              f'which=0&modifiers='
        payload = f'{form_data["callback_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["callback_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={self._session_id}&IW_TrackID_={self._track_id}&' \
                  f'IW_WindowID_={self._window_id}'

        return url, payload

    def get_detail_info(self, selector: scrapy.Selector, id_value: int) -> dict:
        value = selector.xpath(f".//input[@id='IWDBEDIT{id_value}']//@value").get()
        value = selector.xpath(f".//textarea[@id='IWDBTEXT{id_value}']//text()").get() if not value else value
        label = selector.xpath(f".//span[@id='IWLABEL{id_value}']//text()").get()
        if label and value is not None:
            label = re.sub(r"[#:]", "", label)
            label = " ".join(label.split()).replace(" ", "_").lower()

            return {label: value.strip()}

        self.logger.error(msg=f"Failed to extract data of 'IWDBEDIT{id_value}'")
        raise Exception("Failed to extract data of 'IWDBEDIT%s' ", id_value)

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
