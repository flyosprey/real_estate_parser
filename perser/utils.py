import time
from typing import Tuple
import re
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

from fp.fp import FreeProxy
from fp.errors import FreeProxyException


def get_proxy(blacklist: list, is_https: bool = True) -> str:
    try:
        proxy = FreeProxy(country_id=['GB', 'US'], https=is_https, elite=True).get()
        if re.sub(r"https?://", "", proxy) in blacklist:
            print(f"Proxy '{proxy}' in blacklist")
            raise FreeProxyException(message=f"Proxy '{proxy}' in blacklist")
    except FreeProxyException:
        proxy = retry_get_proxy(blacklist=blacklist)

    print(proxy)
    return proxy


def retry_get_proxy(blacklist: list, attempt: int = 1) -> str:
    print("Retry to get proxy!")
    max_attempt = 1000000000000000000000
    if attempt <= max_attempt:
        try:
            proxy = FreeProxy(country_id=["US"], https=True).get()
            if re.sub(r"https?://", "", proxy) in blacklist:
                print(f"Proxy '{proxy}' in blacklist")
                raise FreeProxyException(message=f"Proxy '{proxy}' in blacklist")
        except FreeProxyException:
            time.sleep(1)
            attempt += 1
            proxy = retry_get_proxy(blacklist=blacklist, attempt=attempt)

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

