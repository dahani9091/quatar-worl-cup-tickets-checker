from time import sleep
import pandas as pd
from scraper import Scraper
import logging



logging.basicConfig(filename="logger.log",
                    format="%(asctime)s %(message)s")
logger = logging.getLogger('Scraper')
logger.setLevel(logging.DEBUG)
logging.getLogger('requests').setLevel(logging.DEBUG)
logging.getLogger('bs4').setLevel(logging.DEBUG)


if __name__ == "__main__":
    df = pd.read_excel('data/matches.xlsx')
    while True:
        logger.debug("Checking tickets")
        print("-"*50)
        threads = []

        for i in range(df.shape[0]):

            url = df['URL'][i]
            scraper = Scraper(url, logger)
            scraper.start()

            threads.append(scraper)

            # o_url = url.replace("intl", "dom")
            # scraper = Scraper(o_url, logger)
            # scraper.start()

            # threads.append(scraper)

        for thread in threads:
            thread.join()

        print("Done")
        logger.debug("Sleep for 3 seconds")
        sleep(5)