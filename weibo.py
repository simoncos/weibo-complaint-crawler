import time
import random
import platform
from selenium import webdriver
from pprint import pprint
import traceback

from conf import ACCOUNT, PWD
from mongo import MongoHelper

def getHeader():
    headers = [
            {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1"},
            {"user-agent": "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1"},
            {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3"},
            {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"},
            {"user-agent": "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"}
        ]
    return random.choice(headers)

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

def login(driver):
    # Login
    driver.get('http://weibo.com/login.php')
    driver.implicitly_wait(15)
    driver.find_element_by_xpath('//*[@id="loginname"]').clear()
    driver.find_element_by_xpath('//*[@id="loginname"]').send_keys(ACCOUNT)
    driver.find_element_by_xpath('//*[@id="pl_login_form"]/div/div[3]/div[2]/div/input').clear()
    time.sleep(1)
    driver.find_element_by_xpath('//*[@id="pl_login_form"]/div/div[3]/div[2]/div/input').send_keys(PWD)
    time.sleep(1)
    driver.find_element_by_xpath('//*[@id="pl_login_form"]/div/div[3]/div[6]/a').click()
    time.sleep(1)
    print('>> Successfully Logged In!')

def getComplaintUrls(driver):

    # Enter http://service.account.weibo.com
    driver.get('http://service.account.weibo.com/?type=5&status=4')
    page_count = 1
    print('>>>>Begin Crawling Complaint Urls...')
    while True:
        # TODO: if page_count > total, break
        # Iterate list in each page
        print('>>>>>>Page: {}'.format(page_count))
        complaint_urls = []
        for info in driver.find_elements_by_xpath('//div[@id="pl_service_showcomplaint"]/table[@class="m_table"]'
                                                  '/tbody/tr[not(@class)]'):
            # print(info.text)
            # print(info.find_element_by_xpath('td[2]/div[@class="m_table_tit"]/a').get_attribute('href'),
            #       info.find_element_by_xpath('td[3]/a').text,
            #       info.find_element_by_xpath('td[4]/a').text,
            #       )
            # print(info.find_element_by_xpath('td[2]/div[@class="m_table_tit"]/a').get_attribute('href'))
            complaint_urls.append(info.find_element_by_xpath('td[2]/div[@class="m_table_tit"]/a').get_attribute('href'))

        try:
            # Next page
            next = driver.find_element_by_xpath('//a[@class="W_btn_c"][last()]') # if already at last page, will click 上一页
        except:
            print('Next page not found')
            break

        print('>>>>>>>>Writing to Files...')
        with open('complaint_urls.txt', 'a') as f:
            f.write('\n'.join(complaint_urls) + '\n')

        time.sleep(1)
        next.click()
        page_count += 1

def getComplaintDetail(url, driver):
    driver.get(url)

    title = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[1]/div[2]/h2').text

    # Reporters
    crawled_reporter_names = []
    crawled_reports = []
    iter = 0
    while True:
        iter += 1
        print('iter: {}'.format(iter))
        if iter > 6:
            break

        try:
            next_reporter = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[2]/div[1]/div/div[1]/a')
        except:
            next_reporter = None

        if not next_reporter: # single reporters
            reporter = driver.find_element_by_xpath('//div[@class="W_main_half_l"]//div[@class="user bg_blue2 clearfix"]')
            reporter_name = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').text
            reporter_url = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').get_attribute('href')
            reporter_img_url = reporter.find_element_by_xpath('//*[@id="pl_service_common"]/div[2]/div[1]/div/div[2]/div/img').get_attribute('src')
            reporter_gender = reporter.find_element_by_xpath('p[@class="mb"]/img').get_attribute('class')
            reporter_location = reporter.find_element_by_xpath('p[@class="mb"]').text
            reporter_description = reporter.find_element_by_xpath('p[last()]').text
            crawled_reports.append({
                'reporter_url': reporter_url,
                'reporter_name': reporter_name,
                'reporter_img_url': reporter_img_url,
                'reporter_gender': reporter_gender,
                'reporter_location': reporter_location,
                'reporter_description': reporter_description,
            })
            crawled_reporter_names.append(reporter_name)
            break
        else: # multiple reporters
            try:  # StaleElementReferenceException, if no try, will throw not-attached element exception
                next_reporter.click()
                # time.sleep(1)  # if no sleep > 1s, cannot get all reporters

                reporter = driver.find_element_by_xpath(
                    '//div[@class="W_main_half_l"]//div[@class="user bg_blue2 clearfix"]')
                reporter_name = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').text

                if reporter_name in crawled_reporter_names:
                    break
                else:
                    reporter_url = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').get_attribute('href')
                    reporter_img_url = reporter.find_element_by_xpath('//*[@id="pl_service_common"]/div[2]/div[1]/div/div[2]/div/img').get_attribute('src')
                    reporter_gender = reporter.find_element_by_xpath('p[@class="mb"]/img').get_attribute('class')
                    reporter_location = reporter.find_element_by_xpath('p[@class="mb"]').text
                    reporter_description = reporter.find_element_by_xpath('p[last()]').text
                    crawled_reports.append({
                        'reporter_url': reporter_url,
                        'reporter_name': reporter_name,
                        'reporter_img_url': reporter_img_url,
                        'reporter_gender': reporter_gender,
                        'reporter_location': reporter_location,
                        'reporter_description': reporter_description,
                    })
                    crawled_reporter_names.append(reporter_name)
            except:
                continue

    # Reports
    reports = driver.find_elements_by_xpath('//*[@id="pl_service_common"]/div[4]/div[1]/div/div/div/div')
    assert len(crawled_reports) == len(reports)
    for report in reports:
        report_time = report.find_element_by_xpath('p[@class="publisher"]').text.split('举报人陈述时间：')[1]
        report_text = report.find_element_by_xpath('div[@class="feed clearfix"]/div[@class="con"]').text
        reporter_url = report.find_element_by_xpath('div[@class="feed clearfix"]/div[@class="con"]/a').get_attribute(
            'href')

        for r in crawled_reports:
            if r['reporter_url'] == reporter_url:
                r['report_time'] = report_time
                r['report_text'] = report_text

    # print(crawled_reporter_names)
    # print(crawled_reports)

    # Rumorer
    rumorer = driver.find_element_by_xpath('//div[@class="W_main_half_r"]//div[@class="user bg_orange2 clearfix"]')
    rumorer_name = rumorer.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').text
    rumorer_url = rumorer.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').get_attribute('href')
    rumorer_gender = rumorer.find_element_by_xpath('p[@class="mb"]/img').get_attribute('class')
    rumorer_location = rumorer.find_element_by_xpath('p[@class="mb"]').text
    rumorer_description = rumorer.find_element_by_xpath('p[last()]').text
    crawled_rumor = {
        'rumorer_name': rumorer_name,
        'rumorer_url': rumorer_url,
        'rumorer_gender': rumorer_gender,
        'rumorer_location': rumorer_location,
        'rumorer_description': rumorer_description,
    }

    # Rumor
    rumor = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[4]/div[2]/div/div/div/div')
    rumor_time = rumor.find_element_by_xpath('p[@class="publisher"]').text.split('被举报微博 发布时间：')[1].split(' | 原文')[0]
    rumor_url = rumor.find_element_by_xpath('p[@class="publisher"]/a').get_attribute('href')
    rumor_text = rumor.find_element_by_xpath('div[@class="feed bg_orange2 clearfix"]/div[@class="con"]').text
    rumorer_url = rumor.find_element_by_xpath(
        'div[@class="feed bg_orange2 clearfix"]/div[@class="con"]/a').get_attribute('href')
    assert rumorer_url == crawled_rumor['rumorer_url']
    crawled_rumor['rumor_time'] = rumor_time
    crawled_rumor['rumor_url'] = rumor_url
    crawled_rumor['rumor_text'] = rumor_text

    # Official
    official_text = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[3]/div/div/p').text

    # Looks
    crawled_looks = []
    for look in rumor.find_elements_by_xpath('//*[@id="pl_service_looker"]/div/ul/li'):
        looker_url = look.find_element_by_xpath('a').get_attribute('href')
        looker_name = look.find_element_by_xpath('a').get_attribute('title')
        crawled_looks.append([looker_url, looker_name])

    return {
        'title': title,
        'reports': crawled_reports,
        'rumor': crawled_rumor,
        'official': official_text,
        'looks': crawled_looks
    }

def getComplaintDetails(driver):
    print('>>>>Begin Crawling Complaint Details...')
    mongo = MongoHelper()
    complaints = []
    with open('complaint_urls.txt') as f:
        page_count = 0
        while True:
            page_count += 1
            url = f.readline()
            if str(url) == '':
                break
            print('\nComplaint {}, URL: {}'.format(page_count, url))
            try:
                complaint = getComplaintDetail(url, driver)
                print(complaint)
                complaints.append({'url': url, **complaint})
            except:
                try:
                    print('got exception for url: {}, msg: {}, retrying...'.format(url, traceback.format_exc()))
                    complaint = getComplaintDetail(url, driver)
                    print(complaint)
                    complaints.append({'url': url, **complaint})
                except:
                    print('retry failed for url: {}'.format(url))
            if len(complaints) == 2:
                mongo.update(complaints)
                complaints = []

            # break # debug
        mongo.update(complaints)


if __name__ == '__main__':
    driver = getChrome(headless=True)
    login(driver)
    # getComplaintUrls(driver)

    # pprint(getComplaintDetail('http://service.account.weibo.com/show?rid=K1CaP8wxf7K4j', driver))
    # pprint(getComplaintDetail('http://service.account.weibo.com/show?rid=K1CaP8wxd7K8j', driver))

    getComplaintDetails(driver)