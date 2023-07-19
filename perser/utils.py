import time
from typing import Tuple
import re
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

from fp.fp import FreeProxy
from fp.errors import FreeProxyException


def get_random_user_agent() -> Tuple[str, str]:
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    # It is not the best way, however in some very few cases we receive user_agent without version of chrome
    for limit in range(15):
        user_agent = user_agent_rotator.get_random_user_agent()
        chrome_version = re.search(r"Chrome/(\d+)?\.", user_agent)
        chrome_version = chrome_version[1] if chrome_version else chrome_version
        if chrome_version:
            return user_agent, chrome_version
    raise Exception("ERROR: Cannot find user agent with chrome version!")


def get_proxy(blacklist: list, is_https: bool = True) -> str:
    try:
        proxy = FreeProxy(country_id=['GB'], https=is_https, elite=True).get(repeat=True)
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
            proxy = FreeProxy(country_id=['US', 'DE'], https=True).get()
            if re.sub(r"https?://", "", proxy) in blacklist:
                print(f"Proxy '{proxy}' in blacklist")
                raise FreeProxyException(message=f"Proxy '{proxy}' in blacklist")
        except FreeProxyException:
            time.sleep(1)
            attempt += 1
            proxy = retry_get_proxy(blacklist=blacklist, attempt=attempt)

        return proxy
    raise Exception("Max retry of getting proxy")


