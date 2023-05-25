import time
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

### Setup Driver ###
url = "https://food.grab.com/ph/en/"
chrome_options = webdriver.ChromeOptions()
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134"
chrome_options.add_argument(f'user-agent={user_agent}')
chrome_options.add_argument("--incognito")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=chrome_options)
driver.get(url)


### Accept Cookies ###
try:
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Accept")]'))).click()
except TimeoutException:
    pass

### Fill Location ###
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-layout")))

location_input = driver.find_element(By.ID, 'location-input')
location_input.click()
time.sleep(2)
location_input.clear()

location_input.send_keys("Solar Philippines - Philamlife Tower - 20th/F Philamlife Tower, 8767 Paseo De Roxas St, Bel-Air, Makati City, Metro Manila, NCR, 1209")

submit_button = driver.find_element(By.CSS_SELECTOR, '.ant-btn.submitBtn___2roqB.ant-btn-primary')
submit_button.click()

WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-layout")))

### Scroll to bottom ###
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height


### Extract Restaurant Data ###
layout_div = driver.find_element(By.CSS_SELECTOR, '.ant-layout')
restaurant_names = layout_div.find_elements(By.CSS_SELECTOR, '.name___2epcT')
names = [name.text for name in restaurant_names]
manila_restaurants_dataset = pd.DataFrame(names, columns=['Restaurant'])
url_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/ph/en/restaurant')]")
url_elements_list = []
for url_element in url_elements:
    url_elements_list.append(url_element.get_attribute("href"))
url_elements_list = url_elements_list[10:]


### create dataframe ###
manila_restaurants_dataset_temp = pd.DataFrame(url_elements_list, columns = ['url'])

manila_restaurants_dataset = pd.concat([manila_restaurants_dataset, manila_restaurants_dataset_temp], axis=1, join='inner')

manila_restaurants_dataset['Latitude'] = ''
manila_restaurants_dataset['Longitude'] = ''


### extract restaurant id ###
def extract_restaurant_id(url):
    restaurant_id_pattern = re.compile(r"/([a-zA-Z0-9-]+)$")
    restaurant_id_match = restaurant_id_pattern.search(url)

    if restaurant_id_match:
        return restaurant_id_match.group(1)
    else:
        return None

### get latitude and longitude from api ###
def get_latlng_from_api(restaurant_id):
    api_url = f"https://portal.grab.com/foodweb/v2/merchants/{restaurant_id}"
    headers = {
        "authority": "portal.grab.com",
        "method": "GET",
        "scheme": "https",
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en",
        "dnt": "1",
        "origin": "https://food.grab.com",
        "referer": "https://food.grab.com/",
        "sec-ch-ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "x-country-code": "PH",
        "x-gfc-country": "PH",
        "x-grab-web-app-version": "7JxnV__dTfJZAKF80UUJO",
        "x-hydra-jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnYWEiLCJhdWQiOiJnZnciLCJuYW1lIjoiZ3JhYnRheGkiLCJpYXQiOjE2ODM1NTg0NjQsImV4cCI6MTY4MzU1OTA2NCwibmJmIjoxNjgzNTU4NDY0LCJ2ZXIiOiIxLjE5LjAuMjQiLCJicklEIjoiNDE5ZDc1OTNkZmQ2NjQ0Y2MzZTE5OGRlODFlZDQyZTk4M2Z5NnIiLCJzdXMiOmZhbHNlLCJicklEdjIiOiJmOWQ5NjNjMTEyOTg1M2YyYjYxNmYzNTZkZWU2MmI5ZTZjMnk2ciIsImJyVUlEIjoiZTFkNTU3ODQtOTgzMS00NjdkLTk0YzgtYTZlYzU2Y2U1MzAzIn0.dDZB_ZEGaTZzHPqB6GO8nUFuSvIfujJZUO4mi9NLdPuN3f4MWI0vjeAGx_BPWFTxTI6JcUe3YfzLUHA2uabtLazDe2fLg-OwSmNyIogcIXS8lsunk7r22ju-54up9ASXeDTJFU6Ebn_f6aQ4ajHqLOETE_oeocb_pVowul86WXuq_Qo7yp9jJuAC6GVMdbiOGZgJiRiQhXuy0xPaFOGW-jyQ5wz_qevBMPMO9Xrl56ZD-E1i3RYiQd40BbPvVWB3BvcWuHbVitnHol7YYToezosFpxm3Qj4Hk2BuIEDbyPLGb1nVTI5yHDEerL9_Hj3f-2gPfEPQ5VJ33L5i4y81mgx-recaptcha-token: 03AL8dmw_Z12rIJmB18EL7JYJRnSYBhQr_5Mtab8ajNz9gMoC6kmIr7wITn-fNozK1JUArjDVh85uXapn4gXofDQ2X-mHmuCvaOGBy-ia10Sy-hwLh7nJEz2d6fmx9mjTdW-wWELTzvO_VcEg0hKiWAvnuPuBgIwXs_bFBHUApKft6K2aCG3vax180aEYgFsPwP06rcCQ0u5OpvfsKBJIG84bBmxz88ldPKTIaGfqgGRpPCTFA5RqW60y7aQqX1D2Ca57wOyIOVUqy0Y8mp_jbYim0L5Og3GAuoX6JZuGaHxGDZ3050nAC--C9FPN-bLMae9b31gyDtbeAlgamY99X4dBvVWDOQ1CGUkBRXj_tLAAHUNtuH7b5-rnDLBfsgdhgahHl51dIPMm23TWKvlohcdUH8nF6Hk6e-stR2e1n2kSjqR56xY7GF1Ab5Nah8XIrsCwnohU8K4R5Q9q0CMkiUevyFjHCorqNxdWang1rao__-nVneRN8wnmPlKHSwgRnuB1r3iHkA804C72_WM1hvdzwBfmJZlkMP-wkjx8l1wj_2ZcakQ0Z2eg",
        "x-recaptcha-token": "03AL8dmw_Z12rIJmB18EL7JYJRnSYBhQr_5Mtab8ajNz9gMoC6kmIr7wITn-fNozK1JUArjDVh85uXapn4gXofDQ2X-mHmuCvaOGBy-ia10Sy-hwLh7nJEz2d6fmx9mjTdW-wWELTzvO_VcEg0hKiWAvnuPuBgIwXs_bFBHUApKft6K2aCG3vax180aEYgFsPwP06rcCQ0u5OpvfsKBJIG84bBmxz88ldPKTIaGfqgGRpPCTFA5RqW60y7aQqX1D2Ca57wOyIOVUqy0Y8mp_jbYim0L5Og3GAuoX6JZuGaHxGDZ3050nAC--C9FPN-bLMae9b31gyDtbeAlgamY99X4dBvVWDOQ1CGUkBRXj_tLAAHUNtuH7b5-rnDLBfsgdhgahHl51dIPMm23TWKvlohcdUH8nF6Hk6e-stR2e1n2kSjqR56xY7GF1Ab5Nah8XIrsCwnohU8K4R5Q9q0CMkiUevyFjHCorqNxdWang1rao__-nVneRN8wnmPlKHSwgRnuB1r3iHkA804C72_WM1hvdzwBfmJZlkMP-wkjx8l1wj_2ZcakQ0Z2eg"
    }
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        latitude = data.get("merchant", {}).get("latlng", {}).get("latitude")
        longitude = data.get("merchant", {}).get("latlng", {}).get("longitude")

        if latitude and longitude:
            return latitude, longitude
        else:
            print("Latitude and Longitude not found.")
            return None, None
    else:
        print("Error:", response.status_code)
        return None, None

### Fetch Latitude and Longitude ###
i = 0
for index, row in manila_restaurants_dataset.iterrows():
    restaurant_url = row[1]
    restaurant_name = row[0] 
    print(restaurant_name)
    
    restaurant_id = extract_restaurant_id(restaurant_url)

    if restaurant_id:
        restaurant_latitude, restaurant_longitude = get_latlng_from_api(restaurant_id)
        print(f"Latitude: {restaurant_latitude}, Longitude: {restaurant_longitude}")

        manila_restaurants_dataset.at[i, 'Latitude'] = restaurant_latitude
        manila_restaurants_dataset.at[i, 'Longitude'] = restaurant_longitude
        
    time.sleep(5)
    
    i = i + 1

driver.quit()


### Save Dataset ###
manila_restaurants_dataset['Latitude'] = manila_restaurants_dataset['Latitude'].astype(str)
manila_restaurants_dataset['Longitude'] = manila_restaurants_dataset['Longitude'].astype(str)

manila_restaurants_dataset.to_excel('Restauran_Dataset.xlsx', index=False)

