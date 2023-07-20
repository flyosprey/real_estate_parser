import re
import urllib.parse
import scrapy


class Pagination:
    def get_request(self, data: dict, request_type: str):
        if request_type == "main_page":
            return self._get_main_page_request(data)
        elif request_type == "search_by_permit_number":
            return self._get_search_by_permit_number_request(data)
        elif request_type == "search_by_permit_login":
            return self._get_search_by_permit_login_request(data)
        elif request_type == "permit_details":
            return self._get_permit_details_request(data)
        elif request_type == "collect_page":
            return self._get_collect_page_request(data)
        elif request_type == "previous_page":
            return self._get_previous_page_request(data)
        elif request_type == "callback":
            return self._get_callback_request(data)
        elif request_type == "switch_page":
            return self._get_switch_page_request(data)

        raise Exception("Wrong request_type!")

    @staticmethod
    def _get_switch_page_request(data: dict) -> scrapy.Request:
        meta_data = data["meta_data"]
        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/" \
              f"{meta_data['session_id']}/"
        payload = f'IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}'

        return scrapy.Request(
            method="POST", url=url, callback=meta_data['callback_func'],
            body=payload, headers=meta_data["general_headers"], dont_filter=True,
            meta={'proxy': data["proxy"], "data": meta_data}
        )

    @staticmethod
    def _get_callback_request(data: dict) -> scrapy.Request:
        meta_data, form_data = data["meta_data"], data["form_data"]

        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["action_method"]}.DoOnAsyncClick&x=166&y=18&' \
              f'which=0&modifiers='
        payload = f'{form_data["action_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["action_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}'

        return scrapy.Request(
            method="POST", url=url, callback=data["callback"],
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': data["proxy"], "data": {**meta_data, "callback_func": data["callback_func"]}}
        )

    @staticmethod
    def _get_previous_page_request(data: dict) -> scrapy.Request:
        meta_data, form_data, html = data["meta_data"], data["form_data"], data["html"]

        msgdlgok = re.search(r"var MSGDLGOKIsVisible = (.+?);", html)
        cogrid = re.search(r"FindElem\('COGRID'\)\.value=\"(.+?)\"", html)[1]
        if not msgdlgok or not cogrid:
            raise Exception("Cannot extract msgdlgok or cogrid | Second type of request for 'BACK' button")

        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/" \
              f"{meta_data['session_id']}/"

        msgdlgok, cogrid = msgdlgok[1], urllib.parse.quote(cogrid[1])
        payload = f'MSGDLGOK=%5Eisvisible%3A{msgdlgok}&COGRID={cogrid}&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}&IW_Action={data["action"]}&IW_ActionParam=&' \
                  f'IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}'

        return scrapy.Request(
            method="POST", url=url, callback=data["callback"], dont_filter=True,
            body=payload, headers=meta_data["callback_headers"],
            meta={'proxy': data["proxy"], "data": meta_data}
        )

    @staticmethod
    def _get_collect_page_request(data: dict) -> scrapy.Request:
        meta_data, form_data = data["meta_data"], data["form_data"]

        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["action_method"]}.DoOnAsyncClick&x=166&y=18&' \
              f'which=0&modifiers='
        payload = f'{form_data["action_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["action_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}'

        return scrapy.Request(
            method="POST", url=url, callback=data["callback"],
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': data["proxy"], "data": {**meta_data, "callback_func": data["callback_func"]}}
        )

    @staticmethod
    def _get_permit_details_request(data: dict) -> scrapy.Request:
        meta_data, form_data = data["meta_data"], data["form_data"]

        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["action_method"]}.DoOnAsyncClick&x=166&y=18&' \
              'which=0&modifiers='
        payload = f'EDTPERMITNBR={meta_data["permit_number"]}&{form_data["action_method"]}=&' \
                  f'IW_FormName={form_data["form_name"]}&IW_FormClass={form_data["form_class"]}&' \
                  f'IW_Action={form_data["action_method"]}&IW_ActionParam=&IW_Offset=&' \
                  f'IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}'

        return scrapy.Request(
            method="POST", url=url, callback=data["callback"],
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': data["proxy"], "data": {**meta_data, "callback_func": data["callback_func"]}},
        )

    @staticmethod
    def _get_search_by_permit_login_request(data: dict) -> scrapy.Request:
        meta_data, form_data = data["meta_data"], data["form_data"]

        url = 'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll' \
              f'/{meta_data["session_id"]}/$/callback?callback={form_data["action_method"]}.DoOnAsyncKeyUp&' \
              'which=39&char=%27&modifiers='
        payload = f'EDTPERMITNBR={meta_data["permit_number"]}&IW_FormName={form_data["form_name"]}&' \
                  f'IW_WindowID_={meta_data["window_id"]}&IW_FormClass={form_data["form_class"]}&' \
                  f'IW_Action={form_data["action_method"]}&IW_ActionParam=&' \
                  f'IW_Offset=&IW_SessionID_={meta_data["session_id"]}&IW_TrackID_={meta_data["track_id"]}'

        return scrapy.Request(
            method="POST", url=url, callback=data["callback"],
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': data["proxy"], "data": {**meta_data, "callback_func": data["callback_func"]}}
        )

    @staticmethod
    def _get_main_page_request(data: dict) -> scrapy.Request:
        session_id, track_id, window_id = data["session_id"], data["track_id"], data["window_id"]

        payload = f'IW_SessionID_={session_id}&IW_TrackID_={track_id}&IW_WindowID_={window_id}&' \
                  'IW_dpr=1&IW_width=0&IW_height=0'
        url = "https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/" \
              "webpermitnew/webpermits.dll/" + session_id

        return scrapy.Request(
            method="POST", url=url, callback=data["callback"], dont_filter=True,
            body=payload, headers=data["callback_headers"],
            meta={'proxy': data["proxy"], "data": data}
        )

    @staticmethod
    def _get_search_by_permit_number_request(data: dict) -> scrapy.Request:
        form_data, meta_data = data["form_data"], data["meta_data"]
        callback, proxy, callback_func = data["callback"], data["proxy"], data["callback_func"]
        payload = f'{form_data["action_method"]}=&IW_FormName={form_data["form_name"]}&' \
                  f'IW_FormClass={form_data["form_class"]}IW_Action={form_data["action_method"]}&' \
                  f'IW_ActionParam=&IW_Offset=&IW_SessionID_={meta_data["session_id"]}&' \
                  f'IW_TrackID_={meta_data["track_id"]}&IW_WindowID_={meta_data["window_id"]}'

        url = f'https://cdplusmobile.marioncountyfl.org/pdswebservices/PROD/webpermitnew/webpermits.dll/' \
              f'{meta_data["session_id"]}/$/callback?callback={form_data["action_method"]}.DoOnAsyncClick&x=292&y=34&' \
              f'which=0&modifiers='

        return scrapy.Request(
            method="POST", url=url, callback=callback,
            body=payload, headers=meta_data["callback_headers"], dont_filter=True,
            meta={'proxy': proxy, "data": {**meta_data, "callback_func": callback_func}}
        )
