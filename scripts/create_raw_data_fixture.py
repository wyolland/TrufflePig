import os
import logging

from trufflepig import config
import trufflepig.bchain.getdata as tpbg

def main():

    logging.basicConfig(level=logging.INFO)
    directory = os.path.join(config.PROJECT_DIRECTORY, 'scraped_data')


    frames = tpbg.scrape_or_load_training_data(dict(nodes=[config.NODE_URL]),
                                               directory,
                                               days=20,
                                               stop_after=100,
                                               ncores=8,
                                               current_datetime='2018-02-11')


if __name__ == '__main__':
    main()