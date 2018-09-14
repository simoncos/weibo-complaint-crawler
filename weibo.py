import time
import traceback

from driver import getChrome
from conf import ACCOUNT, PWD
from mongo import MongoHelper
from extract import *
from selenium.common.exceptions import TimeoutException

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
    try:
        driver.get(url)
    except TimeoutException: # selenium exception type
        print('>>>>>>timeout, retrying')
        driver = getChrome(headless=True)
        login(driver)
        return getComplaintDetail(url, driver)

    title = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[1]/div[2]/h2').text

    print('>>>>>>extractReporters')
    reporters, actual_reporter_count = extractReporters(driver)
    print('>>>>>>extractReports')
    reports = extractReports(driver, reporters)
    print('>>>>>>extractRumor')
    rumor = extractRumor(driver)
    print('>>>>>>extractOfficial')
    official = extractOfficial(driver)
    print('>>>>>>extractLooks')
    looks = extractLooks(driver)

    return {
        'title': title,
        'reports': reports,
        'actual_reporter_count': actual_reporter_count,
        'rumor': rumor,
        'official': official,
        'looks': looks
    }

def getComplaintDetails(driver):
    # TODO: get all crawled urls from mongo, if url in the list, continue
    print('>>>>Begin Crawling Complaint Details...')
    mongo = MongoHelper()
    crawled_urls = mongo.getCrawledUrls()
    complaints = []
    with open('complaint_urls.txt') as f:
        page_count = 0
        while True:
            page_count += 1
            url = f.readline().strip()
            if str(url) == '':
                print('>>>>All Complaints Crawling Completed!')
                break

            print('\n>>>>>>Complaint {}, URL: {}'.format(page_count, url))
            if url in crawled_urls:
                print('Skip Crawled Url')
                continue
            try:
                time.sleep(2)
                complaint = getComplaintDetail(url, driver)
                print(complaint)
                complaints.append({'url': url, **complaint})
            except:
                print('>>>>>>Got Exception: {}'.format(url, traceback.format_exc()))

            complaint_count = len(complaints)
            if complaint_count == 2:
                print('>>>>>>Writing {} complaints to mongo...'.format(complaint_count))
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