import json
from pathlib import Path


__root = Path(__file__).parent

with open(__root / "permit_numbers.json", 'r') as file:
    PermitNumbers = json.loads(file.read())["permit_numbers"]

with open(__root / "lua_script.lua", 'r') as file:
    LuaScript = file.read()


class HeadersBehavior:
    def get_callback_headers(self) -> dict:
        general_headers = self.get_base_headers()
        callback_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://cdplusmobile.marioncountyfl.org',
            **general_headers
        }

        return callback_headers

    @staticmethod
    def get_base_headers() -> dict:
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
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        return headers
