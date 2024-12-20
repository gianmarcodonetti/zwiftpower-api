import sys
import re
from os import path, listdir, mkdir, chmod
from stat import S_IXUSR, S_IWUSR, S_IRUSR
from time import sleep
import numpy as np
import pandas as pd
from argparse import ArgumentParser
from selenium import webdriver
from selenium.webdriver.common.by import By
#from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.options import Options  # for suppressing the browser
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException


def scrape(urlpage, headless=False):
    opts = Options()
    if headless:
        opts.headless = True
    scraped_data = {}
    platform = sys.platform
    #driverPath = "./drivers/geckodriver-{}".format(platform)
    driverPath = "./drivers/chromedriver"
    if platform == "win32":
        driverPath += ".exe"
    elif platform in ["linux", "darwin"]:
        chmod(driverPath, S_IXUSR | S_IWUSR | S_IRUSR)
    #with webdriver.Firefox(
    with webdriver.Chrome(
        executable_path=driverPath,
        service_log_path="./drivers/logs/geckodriver-{}_log.log".format(platform),
        options=opts,

    ) as driver:
        driver.implicitly_wait(10)
        for n, url in enumerate(urlpage):
            print("Scraping data from: {}.".format(url))
            finishData = []
            driver.get(url)
            if n == 0:
                print("n=0")
                login_button = driver.find_element(
                    By.XPATH, '//*[@id="login"]/fieldset/div/div[1]/div/a'
                )
                print(login_button)
                login_button.click()
                login_wait = WebDriverWait(driver, 10)
                
                username_input = driver.find_elements(By.ID, 'username')[0]
                username_input.send_keys('nicola.mancini@gmail.com') # mettere username
                password_input = driver.find_elements(By.ID, 'password')[0]
                password_input.send_keys('xxxx') # mettere password
                btn = driver.find_elements(By.ID, 'submit-button')[0]
                btn.click()
                            
            raceName = login_wait.until(
                lambda driver: driver.find_element(
                    By.XPATH, '//*[@id="header_details"]/div[1]/h3'
                ).text
            )
            raceName = re.sub(r"[^A-Za-z0-9 ]+", "", raceName)
            print("Downloading data for {}".format(raceName))
            _pages_loaded = WebDriverWait(driver, 10).until(
                lambda driver: len(
                    driver.find_elements(
                        By.XPATH, '//*[@id="table_event_results_final_paginate"]/ul/li'
                    )[1:-1]
                )
                > 0
            )
            pages = driver.find_elements(
                By.XPATH, '//*[@id="table_event_results_final_paginate"]/ul/li'
            )[1:-1]
            nPages = len(pages)
            results = driver.find_element(
                By.XPATH, '//*[@id="table_event_results_final"]/tbody'
            )
            print("Collecting finish data for all riders...")
            for n in range(2, nPages + 2):
                if n > 2:
                    button = driver.find_element(
                        By.XPATH,
                        '//*[@id="table_event_results_final_paginate"]/ul/li[{}]/a'.format(
                            n
                        ),
                    )
                    name1 = (
                        results.find_elements(By.TAG_NAME, "tr")[0]
                        .find_elements(By.TAG_NAME, "td")[2]
                        .text
                    )
                    driver.execute_script("arguments[0].click();", button)
                    while (
                        results.find_elements(By.TAG_NAME, "tr")[0]
                        .find_elements(By.TAG_NAME, "td")[2]
                        .text
                        == name1
                    ):
                        results = driver.find_element(
                            By.XPATH, '//*[@id="table_event_results_final"]/tbody'
                        )
                        sleep(0.5)
                rows = results.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    category = cols[0].text
                    name = toName(cols[2].text)
                    time = finishTime(cols[3].text)
                    # Trova l'elemento <a> all'interno del primo <td>
                    link_element = cols[2].find_element(By.TAG_NAME, "a")

                    # Ottieni l'attributo href
                    href = link_element.get_attribute("href")

                    # Estrai il numero del profilo usando una regex
                    match = re.search(r"z=(\d+)", href)
                    profile_id = match.group(1) if match else None


                    finishData += [{"Name": name, "Category": category, "Time": time, "Id": profile_id}]
                    # finishData += [{"Name": name, "Category": category, "Time": time}]
            print("Found {} riders.".format(len(finishData)))
            toPrimes = driver.find_element(By.XPATH, '//*[@id="zp_submenu"]/ul/li[4]/a')
            toPrimes.click()
            cButtons = driver.find_elements(
                By.XPATH, '//*[@id="table_scroll_overview"]/div[1]/div[1]/button'
            )
            categoryBottons = [
                but for but in cButtons if not (but.text == "" or but.text == "All")
            ]
            pButtons = driver.find_elements(
                By.XPATH, '//*[@id="table_scroll_overview"]/div[1]/div[2]/button'
            )
            primeButtons = [but for but in pButtons if not but.text == ""]
            primeResults = driver.find_element(
                By.XPATH, '//*[@id="table_event_primes"]/tbody'
            )
            while True:
                try:
                    testCell = (
                        primeResults.find_elements(By.TAG_NAME, "tr")[0]
                        .find_elements(By.TAG_NAME, "td")[3]
                        .text
                    )
                except IndexError:
                    sleep(0.5)
                else:
                    break
            presults = {}
            primeButtons.reverse()
            for catBut in categoryBottons:
                category = catBut.text
                print("Collecting prime data for category {}...".format(category))
                presults[category] = {}
                catBut.click()
                for primeBut in primeButtons:
                    prime = primeBut.text
                    presults[category][prime] = {}
                    primeBut.click()
                    testCell2 = testCell
                    while testCell == testCell2:
                        try:
                            testCell2 = (
                                driver.find_element(
                                    By.XPATH, '//*[@id="table_event_primes"]/tbody'
                                )
                                .find_elements(By.TAG_NAME, "tr")[0]
                                .find_elements(By.TAG_NAME, "td")[3]
                                .text
                            )
                        except StaleElementReferenceException:
                            testCell2 = testCell
                        sleep(0.5)

                    testCell = testCell2
                    primeResults = driver.find_element(
                        By.XPATH, '//*[@id="table_event_primes"]/tbody'
                    )
                    rows = primeResults.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        lap = cols[0].text # numero lap, ad esempio 1 2 ...
                        splitName = cols[1].text # nome lap
                        
                        scores = {
                            # toName(cols[n].text): primeTime(cols[n + 1].text, prime)
                            toName(cols[n].text): {
                                "time": primeTime(cols[n + 1].text, prime), 
                                "id": re.search(r"z=(\d+)", cols[n].find_element(By.TAG_NAME, "a").get_attribute("href")).group(1)
                                if re.search(r"z=(\d+)", cols[n].find_element(By.TAG_NAME, "a").get_attribute("href"))
                                else None
                            }
                            for n in range(2, len(cols), 2)
                            if not cols[n].text == ""
                        }
                        combinedName = "{}_{}".format(lap, splitName)
                        presults[category][prime][combinedName] = scores
            scraped_data[raceName] = [formatFinishes(finishData), formatPrimes(presults)]
            print("Closing connection to {}".format(url))
        print("Formatting scraped data...")
    print("Done.")
    return scraped_data


def toName(string):
    # print(string)
    name = string.split("\n")[0]
    # name = re.sub(r'[^A-Za-z0-9 ]+', '', name)
    # name = name.split(' ')[0]+' '+name.split(' ')[1]
    return name


def secsToMS(string):
    flt = float(string)
    return int(flt * 1000)


def hrsToMS(string):
    ints = [int(t) for t in string.split(":")]
    ints.reverse()
    time = 0
    for n, t in enumerate(ints):
        time += 1000 * t * (60**n)
    return time


def toTime(string):
    if len(string.split(".")) == 1:
        return hrsToMS(string)
    else:
        return secsToMS(string)


def finishTime(string):
    timeStrs = string.split("\n")
    if len(timeStrs) == 1:
        return toTime(timeStrs[0])
    else:
        time = toTime(timeStrs[0])
        if (timeStrs[0].split(".") == 1) and (timeStrs.split(".") < 1):
            tString = timeStrs[1].split(".")[1]
            tString = tString.replace("s", "")
            tString = "0." + tString
            if float(tString) < 0.5:
                time -= 1000 - secsToMS(tString)
            else:
                time += secsToMS(tString)
        return time


def primeTime(string, prime):
    if prime == "First over line":
        if string == "":
            return 0
        else:
            string = string.replace("+", "")
            string = string.replace("s", "")
            return toTime(string)
    else:
        return finishTime(string)


def getFinishPositions(sortP):
    currCat = None
    pos = 1
    positions = []
    for cat in sortP["Category"]:
        if currCat != cat:
            currCat = cat
            pos = 1
        positions += [pos]
        pos += 1
    return positions


def getPrimePositions(sortP):
    currDesc = None
    pos = 1
    positions = []
    for _, row in sortP.iterrows():
        desc = "{}_{}_{}".format(row["Category"], row["Split"], row["Prime"])
        if desc != currDesc:
            currDesc = desc
            pos = 1
        positions += [pos]
        pos += 1
    return positions


def formatFinishes(data):
    categories = list(set([x["Category"] for x in data]))
    # toFile = {"Name": [], "Category": [], "Time (ms)": []}
    toFile = {"Name": [], "Category": [], "Time (ms)": [], "Id": []} # modifica di Nicola
    for rider in data:
        toFile["Name"] += [rider["Name"]]
        toFile["Category"] += [rider["Category"]]
        toFile["Time (ms)"] += [rider["Time"]]
        toFile["Id"] += [rider["Id"]] # aggiunta di Nicola
    fPand = pd.DataFrame.from_dict(toFile)
    sortedData = fPand.sort_values(by=["Category", "Time (ms)"])
    positions = getFinishPositions(sortedData)
    sortedData["Position"] = positions
    return sortedData


def formatPrimes(data):
    #keys = ["Category", "Prime", "Split", "Rider", "Time (ms)"]
    keys = ["Category", "Prime", "Split", "Rider", "Time (ms)", "ID"] # modifica di Nicola
    columns = [[] for _ in keys]
    for key0, data0 in data.items():
        for key1, data1 in data0.items():
            for key2, data2 in data1.items():
                # for name, time in data2.items():
                for name, details in data2.items():    
                    # for index, value in enumerate((key0, key1, key2, name, time)):
                    for index, value in enumerate((key0, key1, key2, name, details["time"], details["id"])):
                        columns[index].append(value)
    pPand = pd.DataFrame(dict(zip(keys, columns)))
    sortedData = pPand.sort_values(by=["Category", "Split", "Prime", "Time (ms)"])
    positions = getPrimePositions(sortedData)
    sortedData["Position"] = positions
    return sortedData


def mkdirAndSave(name, data, filePath):
    resultsPath = "./results/"
    if not path.exists(resultsPath):
        mkdir(resultsPath)
    if not path.exists(path.join(resultsPath, filePath)):
        mkdir(path.join(resultsPath, filePath))
    savePath = path.join(resultsPath,filePath, name + ".csv")
    data.to_csv(savePath, index=False)


# def exportPrimes(primes):
def main():
    parser = ArgumentParser(
        description="Scrape all race time data (finish position and primes)  from a zwiftpower URL"
    )
    parser.add_argument("URL", nargs='+', help="URLs to scrape ZwiftPower results from (must include at least one).")
    parser.add_argument(
        "--saveName",
        "-s",
        help="Specify a filename for the output (default is zwiftpower race title)",
    )
    settings = parser.parse_args()
    results = scrape(settings.URL)
    for n, (name, event) in enumerate(results.items()):
        name = re.sub(r"[^A-Za-z0-9 ]+", "", name)
        if settings.saveName:
            name = f"{settings.saveName}_{n}"
        mkdirAndSave("finishes", event[0], name)
        mkdirAndSave("primes", event[1], name)

if __name__ == "__main__":
    main()
