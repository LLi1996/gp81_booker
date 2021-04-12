"""

"""

import configparser
import logging
import time

from selenium import webdriver


def login_and_go_to_calendar(driver: webdriver.Chrome,
                             cfg: configparser.ConfigParser):
    driver.get(cfg['site']['calendar'])

    if driver.find_elements_by_link_text('Sign In'):  # we need to log in
        logging.info('sign in link found, will go sign in first')

        driver.get(cfg['site']['login'])
        logging.info(f'navigated to {driver.current_url}')

        # todo is there a better way to do this
        user_email_input = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@id='login-form']/div[@class='col-xs-12 col-md-4 col-md-push-4'][2]/div[@class='well']/form[@class='form']/div[@class='form-group'][1]/input[@class='form-control']")
        password_input = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@id='login-form']/div[@class='col-xs-12 col-md-4 col-md-push-4'][2]/div[@class='well']/form[@class='form']/div[@class='form-group'][2]/input[@class='form-control']")
        sign_in_button = driver.find_element_by_xpath(
            "/html/body/div[@class='container']/div[@class='row']/div[@id='mainComponent']/div/div[@id='login-form']/div[@class='col-xs-12 col-md-4 col-md-push-4'][2]/div[@class='well']/form[@class='form']/button[@class='btn btn-primary btn-large']")

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
