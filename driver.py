import platform

from selenium import webdriver


def getChrome(headless=True):
    options = webdriver.ChromeOptions()
    if headless == True:
        options.add_argument('--headless')
    options.add_argument('--disable-notifications')
    options.add_argument("--window-size=1920x1080")
    options.add_argument('--no-sandbox')

    # download and put chromedriver_to the path first
    if platform.system() == 'Windows':
        driver = webdriver.Chrome(executable_path='./chromedriver_win32.exe', chrome_options=options)
    elif platform.system() == 'Linux':
        driver = webdriver.Chrome(executable_path='./chromedriver_linux', chrome_options=options)
    else:
        driver = webdriver.Chrome(executable_path='./chromedriver_mac', chrome_options=options)

    driver.maximize_window()
    return driver

def getFirefox(headless=True):
    options = webdriver.FirefoxOptions()
    if headless == True:
        options.add_argument('--headless')

    options.add_argument('--disable-notifications')
    options.add_argument("--window-size=1920x1080")
    options.add_argument('--no-sandbox')

    # download and put geckodriver to the path first
    driver = webdriver.Firefox(executable_path='./geckodriver', options=options)

    driver.maximize_window()
    return driver