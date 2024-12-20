import time
import os
import re
import logging
import sys
from datetime import datetime
import pandas as pd
from getpass import getpass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

CHROME_DRIVER_PATH = './driver/chromedriver_131_win64.exe'
SLEEP_TIME = 3
ATHLETE_COL = 'athlete_col'
TABLE_EVENT_RESULTS_FINAL="table_event_results_final"

# Constants
login_button = '//*[@id="login"]/fieldset/div/div[1]/div/a'
username_xpath = '//*[@id="username"]'
password_xpath = '//*[@id="password"]'
table_xpath = f'//*[@id={TABLE_EVENT_RESULTS_FINAL}]'

mapping_trophy_to_position = {
    'color:#FDD017': '1',
    'color:#C0C0C0': '2',
    'color:#CD7F32': '3'
}

def set_logger():
    def is_compiled():
        return hasattr(sys, "frozen")  # is the program compiled?

    handlers = [logging.StreamHandler(sys.stdout)]
    if not is_compiled():
        pwd = os.getcwd()
        log_filename = os.path.join("log", "zwiftpower_event_api_" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log')
        handlers.append(logging.FileHandler("{}".format(os.path.join(pwd, log_filename))))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - {%(module)s:%(lineno)s} - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )
    
def main():

    service = Service(executable_path=CHROME_DRIVER_PATH)

    chrome_opts = Options()
    chrome_opts.add_argument('--no-sandbox')
    chrome_opts.add_argument('--headless')
    chrome_opts.add_argument("--allow-running-insecure-content")
    chrome_opts.add_argument("--no-default-browser-check")
    chrome_opts.add_argument("--no-first-run")
    chrome_opts.add_argument("--disable-default-apps")
    chrome_opts.add_argument('--disable-dev-shm-usage')
    chrome_opts.add_argument('--remote-debugging-port=9222')
    
    driver = webdriver.Chrome(options=chrome_opts, service=service)

    start_time = datetime.now()
    screenshots_path = os.path.join("screenshots", "timestamp={}".format(start_time.strftime("%Y-%m-%d_%H:%M:%S")))
    if not os.path.exists(screenshots_path):
        os.makedirs(screenshots_path)
    
    username = input("Username: ") # gianmarco.donetti
    password = getpass("Password: ") # keep it safe
    event_page = input("Event results page: ") # "https://zwiftpower.com/events.php?zid=4616453"
    
    driver.get(event_page)
    time.sleep(SLEEP_TIME)
    driver.maximize_window()
    driver.save_screenshot(os.path.join(screenshots_path, "landing_page.png"))

    # login redirect
    element = driver.find_element(By.XPATH, login_button)
    element.click()
    driver.save_screenshot(os.path.join(screenshots_path, "login.png"))

    driver.find_element(By.XPATH, username_xpath).send_keys(username)
    driver.find_element(By.XPATH, password_xpath).send_keys(password)
    driver.find_element(By.XPATH, '//*[@id="submit-button"]').click()

    driver.save_screenshot(os.path.join(screenshots_path, "inside.png"))

    # reset home page
    driver.get(event_page)
    driver.save_screenshot(os.path.join(screenshots_path, "event_page_reset.png"))

    # scrape the table results
    table_element = driver.find_element(By.XPATH, table_xpath)
    table_html = table_element.get_attribute('outerHTML')

    soup = BeautifulSoup(table_html, 'html.parser')
    table = soup.find('table') # Trova la prima tabella nel codice HTML

    # Estrai i nomi delle colonne
    headers = []
    if table.find('thead'):  # Verifica se esiste un'intestazione
        header_row = table.find('thead').find('tr')
        headers = [ele.text.strip() for ele in header_row.find_all('th')]
        if not headers:  # Se non ci sono elementi 'th', prova con 'td'
            headers = [ele.text.strip() for ele in header_row.find_all('td')]
    elif table.find('tr'): # Se non c'è thead, prendi la prima riga come intestazione.
        header_row = table.find('tr')
        headers = [ele.text.strip() for ele in header_row.find_all('th')]
        if not headers: #Se non ci sono elementi 'th', prova con 'td'
            headers = [ele.text.strip() for ele in header_row.find_all('td')]


    data = []
    if headers:
        starting_row = 1 if table.find('thead') else 1 # Salta la prima riga se già usata come intestazione
    else:
        starting_row = 0 # Nessuna intestazione, prendi tutti i dati dalla prima riga.

    zwift_ids = []
    for row in table.find_all('tr')[starting_row:]: # Se ci sono header, salta la prima riga (o le prime due se c'è thead).
        cols = row.find_all('td')
        cols_stripped = []
        for ele in cols:
            if ele.text.strip() != '':
                if ATHLETE_COL in ele.attrs['class']:
                    zwift_ids.append(ele.find_all('a')[0].attrs['href'].split('z=')[1])
                    cols_stripped.append(ele.find_all('a')[0].attrs['title'])
                else:
                    cols_stripped.append(ele.text.strip())
            else:
                try:
                    #print(f"Get the trophy: {ele.find_all('i')}")
                    value = mapping_trophy_to_position[ele.find_all('i')[0].attrs['style']]
                    #print(f"Value: {value}")
                    cols_stripped.append(value)
                except:
                    cols_stripped.append('')

        data.append([ele for ele in cols_stripped]) # non eliminare celle vuote

    headers[0] = 'cat'
    df = pd.DataFrame(data, columns=headers) if headers else pd.DataFrame(data)

    def parse_gap(x):
        try:
            raw_gap = x.split('+')[1]
            if 's' in raw_gap:
                parsed_gap = float(raw_gap.replace('s', ''))
            else:
                parsed_gap = float(sum(x*y for x,y in zip(map(int, re.findall(r'^(\d+):(\d+)', raw_gap)[0]), [60,1])))
            return parsed_gap
        except:
            return 0

    df['Finish_Time'] = df['Time'].apply(lambda x: x.split('+')[0])
    df['Finish_Gap'] = df['Time'].apply(parse_gap)
    df['Zwift_ID'] = zwift_ids

    event_id = event_page.split('=')[-1]

    df.to_excel(f'results_{event_id}.xlsx', index=False)


if __name__ == '__main__':
    set_logger()
    logging.info(__file__)
    main()