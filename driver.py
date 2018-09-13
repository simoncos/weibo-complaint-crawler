import platform

from selenium import webdriver


def getChrome(headless=True):
    options = webdriver.ChromeOptions()
    if headless == True:
        options.add_argument('headless')
    options.add_argument('--disable-notifications')
    options.add_argument("--window-size=1920x1080")

    # download and put chromedriver_to the path first
    if platform.system() == 'Windows':
        driver = webdriver.Chrome('./chromedriver_win32.exe', chrome_options=options)
    elif platform.system() == 'Linux':
        driver = webdriver.Chrome('./chromedriver_linux', chrome_options=options)
    else:
        driver = webdriver.Chrome('./chromedriver_mac', chrome_options=options)

    driver.maximize_window()
    return driver