import re

import scrapy
from scrapy.cmdline import execute
from scrapy_splash import SplashRequest

from perser.spiders.init_file import SpiderRequirements, LuaScript, HeadersBehavior
from perser.spiders.paginator import Pagination
from perser import utils


class CdplusmobileSpider(scrapy.Spider):
    name = "cdplusmobile"
    allowed_domains = ["cdplusmobile.marioncountyfl.org"]
    start_url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll"

    def __init__(self, *args, **kwargs):
        self.Paginator = Pagination()
        self.HeadersBehavior = HeadersBehavior()
        self.Permits = SpiderRequirements["permit_numbers"]

        self._proxy = SpiderRequirements["proxy"] or utils.get_proxy(is_https=True)
        self._main_page = ""
        self._data = {}
        self._processed_permits = set()

        super().__init__(*args, **kwargs)

    def start_requests(self):
        for permit_number in self.Permits:
            self.logger.info(msg=f"[{permit_number}] Start")
            permit_number = str(permit_number)
            general_headers = self.HeadersBehavior.get_base_headers()
            callback_headers = self.HeadersBehavior.get_callback_headers(base_headers=general_headers)

            splash_args = {'lua_source': LuaScript,
                           'wait': 15, 'url': self.start_url, "headers": general_headers, 'proxy': self._proxy}
            data = {"permit_number": permit_number, "callback_headers": callback_headers,
                    "general_headers": general_headers}

            yield SplashRequest(url=self.start_url, callback=self.parse, method="GET", args=splash_args, dont_filter=True,
                                splash_headers=general_headers, cb_kwargs={"data": data}, endpoint="execute")

    def parse(self, response, **kwargs):
        selector = scrapy.Selector(text=response.text)

        session_id = selector.xpath(".//input[@name='IW_SessionID_']//@value").get()
        track_id = selector.xpath(".//input[@name='IW_TrackID_']//@value").get()
        window_id = selector.xpath(".//input[@name='IW_WindowID_']//@value").get()

        if not session_id or not track_id:
            raise Exception("Cannot extract session_id or track_id")

        data_for_request = {
            "session_id": session_id, "track_id": track_id, "proxy": self._proxy,
            "window_id": window_id, "callback": self.main_page, **kwargs["data"]
        }

        yield self.Paginator.get_request(data=data_for_request, request_type="main_page")

    def main_page(self, response):
        html = utils.normalize_html(html=response.text)
        form_data = self.get_form_data(selector=scrapy.Selector(text=html), action="By Permit")

        data_for_request = {
            "form_data": form_data, "meta_data": response.meta["data"], "callback": self.site_callback,
            "proxy": self._proxy, "callback_func": self.search_by_permit_number
        }

        yield self.Paginator.get_request(data=data_for_request, request_type="search_by_permit_number")

    def search_by_permit_number(self, response):
        html = utils.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        form_data = self.get_form_data(selector=selector, action="PERMIT")
        previous_page_callback = selector.xpath(".//input[@title='Go Back']//@name").get()
        if not previous_page_callback:
            raise Exception("Failed to extract _previous_page_callback")

        permit_number = response.meta["data"]["permit_number"]
        self._data[permit_number] = {}

        data_for_request = {
            "form_data": form_data, "callback": self.site_callback,
            "proxy": self._proxy, "callback_func": self.search_by_permit_login,
            "meta_data": {**response.meta["data"], "previous_page_callback": previous_page_callback}
        }

        yield self.Paginator.get_request(data=data_for_request, request_type="search_by_permit_login")

    def search_by_permit_login(self, response):
        html = utils.normalize_html(html=response.text)
        form_data = self.get_form_data(selector=scrapy.Selector(text=html), action="Continue")

        data_for_request = {
            "form_data": form_data, "meta_data": response.meta["data"], "callback": self.site_callback,
            "proxy": self._proxy, "callback_func": self.permit_details
        }

        yield self.Paginator.get_request(data=data_for_request, request_type="permit_details")

    def permit_details(self, response):
        permit_number = response.meta["data"]["permit_number"]
        self.logger.info(msg=f"[{permit_number}] Passed login")
        html = utils.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)

        self._data[permit_number]["permit_details"] = {}
        for _id in range(1, len(selector.xpath(".//span[contains(@id, 'IWLABEL')]")) + 1):
            self._data[permit_number]["permit_details"].update(self.get_detail_info(selector=selector, id_value=_id))

        button_pages_to_visit = selector.xpath(".//div[@id='RGNBUTTON']//input/@value").getall()
        self._main_page = selector.xpath(".//span[@id='LBLPAGEID']//text()").get()

        action = selector.xpath(".//div[@id='RGNBUTTON']//input/@value").get()
        form_data = self.get_form_data(selector=selector, action=action)

        data_for_request = {
            "form_data": form_data, "callback": self.site_callback,
            "proxy": self._proxy, "callback_func": self.collect_page,
            "meta_data": {**response.meta["data"], "button_pages_to_visit": button_pages_to_visit,
                          "visited_pages": set(), "duple_page": 0, "previous_page": "", "visited_button_pages": set()}
        }
        self.logger.info(msg=f"[{response.meta['data']['permit_number']}] Extracted: Permit Details")
        yield self.Paginator.get_request(data=data_for_request, request_type="collect_page")

    def collect_page(self, response):
        meta_data = response.meta["data"]
        html = utils.normalize_html(html=response.text)
        selector = scrapy.Selector(text=html)
        current_page = selector.xpath(".//span[@id='LBLPAGEID']//text()").get()
        self.logger.info(msg=f"[{meta_data['permit_number']}] Visit: '{current_page}'")

        meta_data["duple_page"] = meta_data["duple_page"] + 1 if current_page == meta_data["previous_page"] else 0

        if not meta_data["button_pages_to_visit"] and meta_data['permit_number'] not in self._processed_permits:
            self._processed_permits.add(meta_data['permit_number'])
            yield {meta_data['permit_number']: self._data[meta_data['permit_number']]}
        else:

            button_pages = self.get_button_pages(selector=selector, current_page=current_page)
            action = meta_data["previous_page_callback"]
            if self._main_page == current_page or (current_page not in meta_data["visited_pages"] and button_pages):
                meta_data["button_pages_to_visit"] += [
                    button_page for button_page in button_pages if button_page not in meta_data["visited_button_pages"]
                ]
                if meta_data["button_pages_to_visit"]:
                    action = meta_data["button_pages_to_visit"].pop(-1)
            elif meta_data["duple_page"] == 0 and not selector.xpath(".//input[contains(@id, 'GUESTLOGIN')]"):
                key_name = utils.normalize_key(key=current_page)
                self._data[meta_data['permit_number']][key_name] = self.get_page_data(selector=selector)
                self.logger.info(msg=f"[{meta_data['permit_number']}] Extracted data: '{current_page}'")

            meta_data["previous_page"] = current_page
            meta_data["visited_pages"].add(current_page)
            meta_data["visited_button_pages"].add(action)

            form_data = self.get_form_data(selector=selector, action=action)
            if meta_data["duple_page"] >= 3:
                meta_data["duple_page"] = 0
                data_for_request = {
                    "form_data": form_data, "meta_data": response.meta["data"], "callback": self.collect_page,
                    "proxy": self._proxy, "action": action, "html": html
                }

                yield self.Paginator.get_request(data=data_for_request, request_type="previous_page")
            else:
                data_for_request = {
                    "form_data": form_data, "meta_data": response.meta["data"], "callback": self.site_callback,
                    "proxy": self._proxy, "callback_func": self.collect_page
                }
                yield self.Paginator.get_request(data=data_for_request, request_type="callback")

    def get_button_pages(self, selector: scrapy.Selector, current_page: str) -> list:
        button_pages = []
        if current_page != self._main_page:
            button_pages = set(selector.xpath(".//div[@id='RGNBUTTON']//input[not(@disabled)]//@value").getall())

        return button_pages

    def get_page_data(self, selector: scrapy.Selector) -> list:
        result = []
        for id_value in range(1, len(selector.xpath("//span[contains(@id, 'LABEL')]").getall()) + 1):
            result.append(self.get_detail_info(selector=selector, id_value=id_value))

        columns = selector.xpath(".//table[contains(@id, 'div0')]//"
                                 "table[contains(@id, 'ID_')]//span[contains(@id, 'T')]/text()").getall()
        if not columns:
            return []

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

        return result

    def _generate_key_for_data(self, current_page: str) -> str:
        page_words = current_page.split()
        key_name = ""
        for word in page_words:
            key_name = f"{key_name}_{word.lower()}".strip("_")
            if not self._data.get(word):
                break

        return key_name

    def get_detail_info(self, selector: scrapy.Selector, id_value: int) -> dict:
        value = selector.xpath(f".//input[@id='IWDBEDIT{id_value}']//@value").get()
        value = selector.xpath(f".//textarea[@id='IWDBTEXT{id_value}']//text()").get() if not value else value
        label = selector.xpath(f".//span[@id='IWLABEL{id_value}']//text()").get()
        if label and value is not None:
            label = utils.normalize_key(key=label)

            return {label: value.strip()}
        elif not label and not value:
            return {}

        self.logger.error(msg=f"Failed to extract data of 'IWDBEDIT{id_value}'")
        raise Exception("Failed to extract data of 'IWDBEDIT%s' ", id_value)

    def get_form_data(self, selector: scrapy.Selector, action: str) -> dict:
        form_name = selector.xpath(".//input[@name='IW_FormName']//@value").get()
        form_class = selector.xpath(".//input[@name='IW_FormClass']//@value").get()

        action_method = selector.xpath(f".//input[contains(@value, '{action}')]//@name").get()
        if not action_method:
            action_method = selector.xpath(f".//input[@name='{action}']//@id").get()
        if not action_method:
            action_method = selector.xpath(f".//span[contains(@id, '{action}')]//@name").get()

        if action_method or form_class or form_name:
            return {"form_name": form_name, "form_class": form_class, "action_method": action_method}

        self.logger.error(msg="Failed to get form_data")
        raise Exception("Failed to get form_data")

    def site_callback(self, response):
        meta_data = response.meta["data"]

        session_id_match = re.search(r"IW_SessionID_\": \"(.+?)\"", response.text)
        meta_data["session_id"] = session_id_match[1] if session_id_match else meta_data["session_id"]

        track_id_match = re.search(r"<trackid>(.*?)</trackid>", response.text)
        track_id_match = re.search(r"IW_TrackID_\": (.+?)}", response.text) if not track_id_match else track_id_match
        meta_data["track_id"] = track_id_match[1].strip() if track_id_match else meta_data["track_id"]

        data_for_request = {"meta_data": meta_data, "proxy": self._proxy}

        yield self.Paginator.get_request(data=data_for_request, request_type="switch_page")



if __name__ == "__main__":
    execute()
