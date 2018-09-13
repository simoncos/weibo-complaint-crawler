import time
from selenium import webdriver

from driver import getChrome


class Cookie(object):
    url = 'http://weibo.com/login.php'
    def __init__(self):
        self.browser = getChrome()

    def getWeiboCookie(self):
        cookie_dic = {}
        cookies = self.browser.get_cookies()
        self.browser.close()
        for cookie in cookies:
            if 'name' in cookie and 'value' in cookie:
                cookie_dic[cookie['name']]=cookie['value']
        return cookie_dic

if __name__ == '__main__':
    cookie = Cookie()
    print(cookie.getWeiboCookie())