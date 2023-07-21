import time
import re
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

from fp.fp import FreeProxy
from fp.errors import FreeProxyException


def get_random_user_agent() -> (str, str):
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    # It is not the best way, however in some very few cases we receive user_agent without version of chrome
    for limit in range(11):
        user_agent = user_agent_rotator.get_random_user_agent()
        chrome_version = re.search(r"Chrome/(\d+)?\.", user_agent)
        chrome_version = chrome_version[1] if chrome_version else chrome_version
        if chrome_version:
            return user_agent, chrome_version
    raise Exception("ERROR: Set better user agent!")


def get_proxy(is_https: bool = True) -> str:
    try:
        proxy = FreeProxy(country_id=['US'], https=is_https, elite=True).get()
    except FreeProxyException:
        proxy = retry_get_proxy(is_https=is_https)

    print(proxy)
    return proxy


def retry_get_proxy(is_https: bool, attempt: int = 1) -> str:
    print("Retry to get proxy!")
    max_attempt = 10
    if attempt <= max_attempt:
        try:
            proxy = FreeProxy(country_id=["US"], https=is_https).get()
        except FreeProxyException:
            time.sleep(1)
            attempt += 1
            proxy = retry_get_proxy(attempt=attempt, is_https=is_https)

        return proxy
    raise Exception("Max retry of getting proxy")


def normalize_key(key: str) -> str:
    key = re.sub(r"[#:]", "", key)
    key = " ".join(key.split()).replace(" ", "_").lower()

    return key


def normalize_html(html: str) -> str:
    bad_tags = re.findall(r"</?[A-Z]+?[\s>]|[A-Z]+?=\"", html)
    if not bad_tags:
        return html

    bad_tags = set(bad_tags)
    for bad_tag in bad_tags:
        html = html.replace(bad_tag, bad_tag.lower())

    return html
