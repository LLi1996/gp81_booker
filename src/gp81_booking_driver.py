"""

"""

import argparse
import configparser
import datetime
import logging
import time

from selenium import webdriver

from src import gp81_flexbooker as booker


def main():
    ap = argparse.ArgumentParser(description='gp81 booker')
    ap.add_argument('--wednesday_noon', action='store_true',
                    help='flag to wait till 1 sec past 12 on Wednesdays before any booking action')
    ap.add_argument('--config_file', default='./config.ini',
                    help='path to the config file')
    ap.add_argument('--logging_level', default='INFO',
                    help='choice of [CRITICAL, ERROR, WARNING, INFO, DEBUG], default: debug')
    args = ap.parse_args()

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=args.logging_level)

    logging.info(f'setting up config from {args.config_file}')
    cfg = configparser.ConfigParser()
    cfg.read(args.config_file)

    logging.info(f'setting up selenium chrome driver')
    driver = webdriver.Chrome()
    driver.implicitly_wait(int(cfg['site']['implicit_wait_secs']))

    if args.wednesday_noon:
        if datetime.date.today().isoweekday() != 3:
            logging.info('seems like it is not Wednesday and --wednesday_noon flag is set, no action taken')
        else:
            booking_go_time = datetime.datetime(1, 1, 1, 12, 0, 1).time()
            sleep_interval = float(cfg['booking']['wednesday_noon_sleep_wait_interval'])
            while 1:
                if datetime.datetime.now().time() > booking_go_time:
                    logging.info('it\'s noon, starting booking process')
                    break
                else:
                    logging.info(f'current time is {datetime.datetime.now()}, booking go time is {booking_go_time},'
                                 f' sleeping {sleep_interval} secs')
                    time.sleep(sleep_interval)

    booking_targets = booker.parse_booking_rule(cfg['booking']['rule'])
    logging.info(f'booking: {[booker.booking_target_to_human_readable(x) for x in booking_targets]}')

    try:
        booker.login_and_go_to_calendar(driver, cfg)
        upcoming_bookings = booker.get_upcoming_bookings(driver, cfg)
        logging.info(f'preexisting bookings (these will be skipped):'
                     f' {sorted([booker.booking_target_to_human_readable(x) for x in upcoming_bookings])}')

        for target in [x for x in booking_targets if x not in upcoming_bookings]:
            try:
                booker.book(driver, cfg, target)
            except Exception as e:
                logging.error(f'failed to book {booker.booking_target_to_human_readable(target)}')
                logging.exception(e)
    finally:
        logging.info('shutting down driver')
        driver.close()


if __name__ == '__main__':
    main()
