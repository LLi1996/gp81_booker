"""

"""

import configparser
import datetime
import logging
import time
from typing import Tuple

from selenium import webdriver

_ISO_WEEKDAY_2_FIRST_SESSION = {
    1: (datetime.datetime(1, 1, 1, 6, 0, 0), 7),
    2: (datetime.datetime(1, 1, 1, 6, 0, 0), 7),
    3: (datetime.datetime(1, 1, 1, 6, 0, 0), 7),
    4: (datetime.datetime(1, 1, 1, 6, 0, 0), 7),
    5: (datetime.datetime(1, 1, 1, 6, 0, 0), 7),
    6: (datetime.datetime(1, 1, 1, 8, 0, 0), 6),
    7: (datetime.datetime(1, 1, 1, 8, 0, 0), 6)
}

_SESSION_LENGTH = datetime.timedelta(hours=2, minutes=20)

_ISO_WEEKDAY_2_SESSIONS = {
    iso_weekday: [(start + i * _SESSION_LENGTH).time() for i in range(num_sessions)]
    for iso_weekday, (start, num_sessions) in _ISO_WEEKDAY_2_FIRST_SESSION.items()
}

_ISO_WEEKDAY_SESSION_START_2_SLOT_NUMBER = {
    (iso_weekday, session): i
    for iso_weekday, sessions in _ISO_WEEKDAY_2_SESSIONS.items()
    for i, session in enumerate(sessions)
}


def get_current_booking_date_range(today: datetime.datetime = None) -> Tuple[datetime.date, datetime.date]:
    """
    Spots are released on Wednesdays to the Saturday two weeks out

    :param today:

    :return:
    """
    today = datetime.datetime.today() if today is None else today
    last_wednesday = today - datetime.timedelta(days=(today.isoweekday() - 3) % 7)
    if today.isoweekday() == 3 and today.hour < 12:  # Wednesday before noon, when bookings are released
        last_wednesday = last_wednesday - datetime.timedelta(days=7)
    saturday_two_weeks_out = last_wednesday + datetime.timedelta(days=17)
    return (today.date(), saturday_two_weeks_out.date())


def login_and_go_to_calendar(driver: webdriver.Chrome,
                             cfg: configparser.ConfigParser):
    driver.get(cfg['site']['calendar'])

    if driver.find_elements_by_link_text('Sign In'):  # we need to log in
        logging.info('sign in link found, will go sign in first')

        driver.get(cfg['site']['login'])
        logging.info(f'navigated to {driver.current_url}')

        # todo is there a better way to do this
        user_email_input = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@id='login-form']"
            "/div[@class='col-xs-12 col-md-4 col-md-push-4'][2]/div[@class='well']/form[@class='form']"
            "/div[@class='form-group'][1]/input[@class='form-control']")
        password_input = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@id='login-form']"
            "/div[@class='col-xs-12 col-md-4 col-md-push-4'][2]/div[@class='well']/form[@class='form']"
            "/div[@class='form-group'][2]/input[@class='form-control']")
        sign_in_button = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@id='login-form']"
            "/div[@class='col-xs-12 col-md-4 col-md-push-4'][2]/div[@class='well']/form[@class='form']"
            "/button[@class='btn btn-primary btn-large']")

        logging.info('filling in user email and password')
        user_email_input.send_keys(cfg['credential']['email'])
        password_input.send_keys(cfg['credential']['password'])

        sign_in_button.click()
        time.sleep(1)  # for site to load, too lazy to add in correct waiting here

        # some basic sanity checks
        if driver.current_url.lower() == cfg['site']['calendar']:
            logging.info(f'signed in, now on {driver.current_url}')
        elif driver.current_url.lower() == cfg['site']['login']:
            raise RuntimeError(f'Still on {driver.current_url}, seems like login failed, please check the configured'
                               f' user email and password')
        else:
            logging.warning(f"was expecting automated navigation to {cfg['site']['calendar']} after login, we are at"
                            f" {driver.current_url} instead. Unsure if login failed, will navigate to"
                            f" {cfg['site']['calendar']}")
            driver.get(cfg['site']['calendar'])
    else:  # no need to log in again, navigate to the calendar page
        logging.info(f'no sign in link found, already logged in and on {driver.current_url}')


def get_booking_date_of_first_column(driver: webdriver.Chrome,
                                     cfg: configparser.ConfigParser) -> datetime.date:
    assert driver.current_url == cfg['site']['calendar']

    day_header = driver.find_element_by_xpath(
        "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
        "/div/div[@id='widget-week-container']/div[@class='widget-week-day'][1]/div[@class='widget-week-day-header']")

    header_text = day_header.text  # this looks like: Fri\nApr 16th
    date_str = header_text.split('\n')[-1][:-2]  # takes out things before the linebreak and after the date numbers
    date_str = f'{(datetime.date.today().year)} {date_str}'  # we assume things are in this year todo is this valid?
    logging.debug(f'header text of first booking column was: {header_text}, we made it {date_str} to parse')
    booking_date = datetime.datetime.strptime(date_str, '%Y %b %d')
    if (booking_date.month == 12 and booking_date.day > 30) or (booking_date.month == 1 and booking_date.day < 10):
        logging.warning(f'we\'re close to the new year, check if the parsed date ({booking_date}) is correct')
    return booking_date
