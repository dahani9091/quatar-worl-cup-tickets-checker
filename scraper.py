import threading
import requests
from bs4 import BeautifulSoup
import logging






class Scraper(threading.Thread):
    def __init__(self, url, logger):
        threading.Thread.__init__(self)
        self.url = url
        self.logger = logger

    def run(self):
        print("Scraping {}".format(self.url))
        self.scrape(self.url)


    def get_page_info(self):

        
        # Get the page content
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
        }

        response = requests.get(self.url, headers=header)
        if response.status_code != 200:
            print("Error fetching page")
            
            exit()
        else:
            content = response.content

        soup = BeautifulSoup(content, 'html.parser')

        # get the page categories
        all_results = soup.select('tbody tr')[:3]
        data = {}

        # get host_vs_opposing
        host = soup.select(".host")[0].text.strip()
        opposing = soup.select(".opposing")[0].text.strip()
        host_vs_opposing = f"{host} vs {opposing}"
        data['host_vs_opposing'] = host_vs_opposing

        # get stadium
        stadium = soup.select(".location")[-1].text.strip()
        data['stadium'] = stadium
        
        # get match number
        match = int(soup.select(".round")[0].text.lower().replace("match","").strip())
        data['match'] = match

        for idx, category in enumerate(all_results):
            cat_dict = {}

            quantity = category.select('.quantity ')

            if quantity:
                cat_dict['is_available'] = "Currently unavailable" not in quantity[0].text
                cat_dict['text'] = quantity[0].text.strip()
            else:
                print("None")
                cat_dict['is_available'] = False
                cat_dict['text'] = "None"
            data[f'category {idx+1}'] = cat_dict

        if (data['category 1']['is_available'] | data['category 2']['is_available'] | data['category 3']['is_available']):
            self.logger.debug(
                f"True condition ---  Url: {self.url}\n{data}"
            )

        elif (   "Currently unavailable" not in data['category 1']['text'] \
            or "Currently unavailable" not in data['category 2']['text'] \
            or "Currently unavailable" not in data['category 3']['text']):
            self.logger.debug(
                f"Weird condition ---  Url: {self.url}\n{data}"
            )
        return data

    def scrape(self, url):
        res = self.get_page_info()
        print("{} has been scraped".format(url))