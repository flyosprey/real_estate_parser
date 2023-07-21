# How it works?
1. `docker pull scrapinghub/splash`
2. `docker run -it -p 8050:8050 --rm scrapinghub/splash` 
3. `pip install requirements.txt`
4. Fill `permit_numbers.json` by numbers you want to extract info
5. Run `scrapy crawl cdplusmobile.py -o result.json`