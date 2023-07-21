import json
from pathlib import Path

from perser import utils


__root = Path(__file__).parent

with open(__root / "spider_requirements.json", 'r') as file:
    SpiderRequirements = json.loads(file.read())

with open(__root / "lua_script.lua", 'r') as file:
    LuaScript = file.read()


class HeadersBehavior:
    @staticmethod
    def get_callback_headers(base_headers: dict) -> dict:
        callback_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://cdplusmobile.marioncountyfl.org',
            **base_headers
        }

        return callback_headers

    @staticmethod
    def get_base_headers() -> dict:
        user_agent, chrome_version = utils.get_random_user_agent()
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7,ru-RU;q=0.6,ru;q=0.5,uk-UA;q=0.4,uk;q=0.3',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': user_agent,
            # 'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            'sec-ch-ua': f'"Not.A/Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"',
            # 'sec-ch-ua': f'"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        return headers
