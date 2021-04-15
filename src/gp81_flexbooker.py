"""

"""
import calendar
import configparser
import datetime
import logging
import operator
import time
from collections import defaultdict
from typing import Tuple, List, Set

import selenium.common.exceptions
from selenium import webdriver

_DAY_OF_WEEK_NAME_2_ISO_WEEKDAY = {
    name.lower(): week_day + 1
    for week_day, name in enumerate(calendar.day_name)
}

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
    (iso_weekday, session): i + 1
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


def parse_booking_rule(rule_csv: str,
                       today: datetime.date = None) -> List[Tuple[datetime.date, int, datetime.time]]:
    """

    :param rule_csv: comma separated value of: <full day of week name> hh:mm
    :param today:
    :return:
    """
    start_available_date, end_available_date = get_current_booking_date_range(today=today)
    iso_weekday_2_dates = defaultdict(list)
    date = start_available_date
    while date <= end_available_date:
        iso_weekday_2_dates[date.isoweekday()].append(date)
        date = date + datetime.timedelta(days=1)

    targets_with_priority = set()
    for priority, rule in enumerate([x.strip().lower() for x in rule_csv.split(',')]):
        day_of_week, session_start = rule.split(' ')
        start_hour, start_minute = session_start.split(':')
        iso_weekday = _DAY_OF_WEEK_NAME_2_ISO_WEEKDAY[day_of_week]
        session_start = datetime.datetime(1, 1, 1, int(start_hour), int(start_minute), 0).time()
        if (iso_weekday, session_start) in _ISO_WEEKDAY_SESSION_START_2_SLOT_NUMBER:
            for date in iso_weekday_2_dates[iso_weekday]:
                targets_with_priority.add((priority, date, iso_weekday, session_start))
        else:
            raise RuntimeError(f'rule: {rule} is not a valid gp slot')

    # sort by input rule priority and then by date
    targets_with_priority = list(targets_with_priority)
    targets_with_priority = sorted(targets_with_priority, key=operator.itemgetter(1), reverse=True)
    targets_with_priority = sorted(targets_with_priority, key=operator.itemgetter(0))
    return [(date, iso_weekday, session_start) for (_, date, iso_weekday, session_start) in targets_with_priority]


def get_upcoming_bookings(driver: webdriver.Chrome,
                          cfg: configparser.ConfigParser) -> Set[Tuple[datetime.date, int, datetime.time]]:
    if 'calendar' not in driver.current_url:
        driver.get(cfg['site']['calendar'])
    manage_upcoming_bookings_button = driver.find_element_by_link_text('Manage Upcoming Bookings')
    manage_upcoming_bookings_button.click()

    upcoming_booking_slot = 1
    upcoming_bookings = set()
    while 1:
        try:
            slot = driver.find_element_by_xpath(
                f"/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@class='row']"
                f"/div[@class='col-xs-12'][1]/div[{upcoming_booking_slot}]/div[@class='apptBox']/p[1]")
            booking_datetime = datetime.datetime.strptime(slot.text.split(' / ')[0].strip(), '%m/%d/%Y %I:%M %p')
            if booking_datetime < datetime.datetime.now():
                break
            else:
                upcoming_bookings.add((booking_datetime.date(), booking_datetime.isoweekday(), booking_datetime.time()))
                upcoming_booking_slot += 1
        except selenium.common.exceptions.NoSuchElementException as e:
            break
    return upcoming_bookings


def booking_target_to_human_readable(target: Tuple[datetime.date, int, datetime.time]) -> str:
    date, iso_weekday, session_start = target
    return f'{date.strftime("%Y-%m-%d")} ({calendar.day_abbr[iso_weekday - 1]}) {session_start.strftime("%I:%M %p")}'


def login_and_go_to_calendar(driver: webdriver.Chrome,
                             cfg: configparser.ConfigParser):
    driver.get(cfg['site']['calendar'])

    if driver.find_elements_by_link_text('Sign In'):  # we need to log in
        logging.debug('sign in link found, will go sign in first')

        driver.get(cfg['site']['login'])
        logging.debug(f'navigated to {driver.current_url}')

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

        logging.debug('filling in user email and password')
        user_email_input.send_keys(cfg['credential']['email'])
        password_input.send_keys(cfg['credential']['password'])

        sign_in_button.click()
        time.sleep(1)  # for site to load, too lazy to add in correct waiting here

        # some basic sanity checks
        if driver.current_url.lower() == cfg['site']['calendar']:
            logging.debug(f'signed in, now on {driver.current_url}')
        elif driver.current_url.lower() == cfg['site']['login']:
            raise RuntimeError(f'Still on {driver.current_url}, seems like login failed, please check the configured'
                               f' user email and password')
        else:
            logging.warning(f"was expecting automated navigation to {cfg['site']['calendar']} after login, we are at"
                            f" {driver.current_url} instead. Unsure if login failed, will navigate to"
                            f" {cfg['site']['calendar']}")
            driver.get(cfg['site']['calendar'])
    else:  # no need to log in again, navigate to the calendar page
        logging.debug(f'no sign in link found, already logged in and on {driver.current_url}')


def get_booking_date_of_first_column(driver: webdriver.Chrome,
                                     cfg: configparser.ConfigParser) -> datetime.date:
    assert 'calendar' in driver.current_url

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
    return booking_date.date()


def go_to_another_week(driver: webdriver.Chrome,
                       cfg: configparser.ConfigParser,
                       forward=True):
    assert driver.current_url == cfg['site']['calendar']
    if forward:
        logging.debug('clicking on the NEXT WEEK button')
        button = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
            "/div/div[@id='widget-week-container']/a[@class='pull-right weekButton']")
    else:
        logging.debug('clicking on the PREVIOUS WEEK button')
        button = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
            "/div/div[@id='widget-week-container']/a[@class='pull-left weekButton']")
    button.click()
    time.sleep(.3)


def book(driver: webdriver.Chrome,
         cfg: configparser.ConfigParser,
         target: Tuple[datetime.date, int, datetime.time]):
    logging.info(f'trying to book {booking_target_to_human_readable(target)}')
    date, iso_weekday, session_start = target

    if 'calendar' not in driver.current_url:
        logging.debug(f"on {driver.current_url}, navigating to {cfg['site']['calendar']}")
        driver.get(cfg['site']['calendar'])

    while 1:
        date_of_first_column = get_booking_date_of_first_column(driver, cfg)
        day_diff = (date - date_of_first_column).days
        if day_diff >= 0 and day_diff < 7:  # target date on page, go book
            logging.debug(f'found target date ({date}) on current page (starts on {date_of_first_column})')
            break
        else:
            logging.debug(f'target date ({date}) not on page (starts on {date_of_first_column}) date_diff: {day_diff}')
            if day_diff >= 7:
                go_to_another_week(driver, cfg, forward=True)
            else:
                go_to_another_week(driver, cfg, forward=False)

    col = day_diff + 1
    row = _ISO_WEEKDAY_SESSION_START_2_SLOT_NUMBER[(iso_weekday, session_start)]
    logging.debug(f'determined the session to be at row #{row} col #{col}')

    slot = driver.find_element_by_xpath(
        "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
        f"/div/div[@id='widget-week-container']/div[@class='widget-week-day'][{col}]"
        f"/div[@class='widget-week-day-times']/div/a[@class='selectableTime service40166'][{row}]")

    if 'WAIT LIST' in slot.text:
        logging.warning(f'{booking_target_to_human_readable(target)} has a wait list, no action configured, skipping')
        pass
    else:
        slot.click()

        # usually this info is remembered by the browser/flexbooker but doesn't hurt to always put in
        logging.debug('filling in first name / last name / email / phone')

        first_name = driver.find_element_by_xpath("//input[@id='fieldfirstName']")
        first_name.clear()
        first_name.send_keys(cfg['user']['first_name'])

        last_name = driver.find_element_by_xpath("//input[@id='fieldlastName']")
        last_name.clear()
        last_name.send_keys(cfg['user']['last_name'])

        email = driver.find_element_by_xpath("//input[@id='fieldemail']")
        email.clear()
        email.send_keys(cfg['user']['email'])

        phone = driver.find_element_by_xpath("//input[@id='fieldphone']")
        phone.clear()
        phone.send_keys(cfg['user']['phone'])

        logging.debug(f"<remind by email> is {cfg['booking']['remind_by_email']}"
                      f" and <remind by text> is {cfg['booking']['remind_by_text']}")
        remind_by_email = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
            "/div/div[@class='row customBookingFormRow']/div[@class='col-xs-12']/form[@id='scheduleBookingForm']"
            "/div[@class='row col-spacing-60 col-xs-spacing-30']/div[@class='form-group col-xs-12 col-md-12'][2]"
            "/div[@class='pull-left'][1]/div[@class='checkbox-custom-booking']/label")

        remind_by_text = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
            "/div/div[@class='row customBookingFormRow']/div[@class='col-xs-12']/form[@id='scheduleBookingForm']"
            "/div[@class='row col-spacing-60 col-xs-spacing-30']/div[@class='form-group col-xs-12 col-md-12'][2]"
            "/div[@class='pull-left'][2]/div[@class='checkbox-custom-booking']/label")

        # by default remind by email is clicked and remind by text isn't todo: how do we figure out if it's clicked
        if cfg['booking']['remind_by_email'] == 'false':
            remind_by_email.click()

        if cfg['booking']['remind_by_text'] == 'true':
            remind_by_text.click()

        book = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']"
            "/div/div[@class='row customBookingFormRow']/div[@class='col-xs-12']/form[@id='scheduleBookingForm']"
            "/div[@class='row'][1]/div[@class='col-xs-12 text-center']/button[@class='btn btn-primary btn-primary-1']")
        book.click()
        logging.info(f'{booking_target_to_human_readable(target)} booked')

        make_another_booking = driver.find_element_by_partial_link_text('Make Another Booking')
        make_another_booking.click()
        time.sleep(.3)
