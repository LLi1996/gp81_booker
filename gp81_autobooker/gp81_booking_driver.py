"""

"""

import configparser
import logging

from selenium import webdriver

from gp81_autobooker import gp81_flexbooker

_config_file = './config.ini'


def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level='INFO')

    logging.info(f'setting up config from {_config_file}')
    cfg = configparser.ConfigParser()
    cfg.read(_config_file)

    logging.info(f'setting up selenium chrome driver')
    driver = webdriver.Chrome()
    driver.implicitly_wait(int(cfg['site']['implicit_wait_secs']))

    try:
        gp81_flexbooker.login_and_go_to_calendar(driver, cfg)
    except Exception as e:
        logging.exception(e)
    finally:
        logging.info('shutting down driver')
        driver.close()


if __name__ == '__main__':
    main()
