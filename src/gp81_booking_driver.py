"""

"""

import configparser
import logging

from selenium import webdriver

from src import gp81_flexbooker

_config_file = './config.ini'


def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level='INFO')

    logging.info(f'setting up config from {_config_file}')
    cfg = configparser.ConfigParser()
    cfg.read(_config_file)

    booking_targets = gp81_flexbooker.parse_booking_rule(cfg['booking']['rule'])
    logging.info(f'booking: {sorted([gp81_flexbooker.booking_target_to_human_readable(x) for x in booking_targets])}')

    logging.info(f'setting up selenium chrome driver')
    driver = webdriver.Chrome()
    driver.implicitly_wait(int(cfg['site']['implicit_wait_secs']))

    try:
        gp81_flexbooker.login_and_go_to_calendar(driver, cfg)
        for target in booking_targets:
            gp81_flexbooker.book(driver, cfg, target)
    except Exception as e:
        logging.exception(e)
    finally:
        logging.info('shutting down driver')
        driver.close()


if __name__ == '__main__':
    main()
