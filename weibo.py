import time
import traceback
import os, sys

from driver import getChrome
from conf import ACCOUNT, PWD, IMPLICIT_WAIT_DRIVER, SLEEP_NEXT_COMPLAINTS_PAGE, SLEEP_NEXT_COMPLAINT, \
                 RETRY_COMPLAINT_DETAIL_TIMEOUT_COUNT, RESTART_EXCEPTION_COUNT, RESTART_TIMEOUT_EXCEPTION_COUNT,\
                 SAVE_COMPAINT_BATCH
from mongo import MongoHelper
from extract import *
from selenium.common.exceptions import TimeoutException

def login(driver):
    # Login
    driver.get('http://weibo.com/login.php')
    driver.implicitly_wait(IMPLICIT_WAIT_DRIVER)
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
    print('>> Begin Crawling Complaint Urls...')
    while True:
        # TODO: if page_count > total, break
        # Iterate list in each page
        print('>>>> Page: {}'.format(page_count))
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

        print('>>>> Writing to Files...')
        with open('complaint_urls.txt', 'a') as f:
            f.write('\n'.join(complaint_urls) + '\n')

        time.sleep(SLEEP_NEXT_COMPLAINTS_PAGE)
        next.click()
        page_count += 1

def getComplaintDetail(url, driver, retry=0):
    try:
        driver.get(url)
    except TimeoutException: # selenium exception type
        if retry >= RETRY_COMPLAINT_DETAIL_TIMEOUT_COUNT:
            print('>>>> TimeoutException occurs in {} Retries, Raise'.format(retry))
        else:
            retry += 1
            print('>>>> Timeout, retrying {}...'.format(retry))
            # driver = getChrome(headless=True)
            # login(driver)
            return getComplaintDetail(url, driver, retry)

    try:
        title = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[1]/div[2]/h2').text
    except:
        title = '' # not necessary

    print('>>>> Begin extractReporters')
    reporters, actual_reporter_count = extractReporters(driver)
    print('>>>> Begin extractReports')
    reports = extractReports(driver, reporters)
    print('>>>> Begin extractRumor')
    rumor = extractRumor(driver)
    print('>>>> Begin extractOfficial')
    official = extractOfficial(driver)
    print('>>>> Begin extractLooks')
    looks = extractLooks(driver)

    return {
        'title': title,
        'reports': reports,
        'actual_reporter_count': actual_reporter_count,
        'rumor': rumor,
        'official': official,
        'looks': looks
    }

def restart_program():
  python = sys.executable
  os.execl(python, python, * sys.argv)

def getComplaintDetails(driver):
    # TODO: get all crawled urls from mongo, if url in the list, continue
    print('>>>> Begin Crawling Complaint Details...')
    mongo = MongoHelper()
    crawled_urls = mongo.getCrawledUrls()
    complaints = []
    exception_count = 0
    timeout_exception_count = 0
    with open('complaint_urls.txt') as f:
        page_count = 0
        while True:
            # restart when come across too many timeouts
            if timeout_exception_count >= RESTART_TIMEOUT_EXCEPTION_COUNT:
                print(f'>>>> Timeout Excepiton reach {RESTART_EXCEPTION_COUNT}, try to restart program!')
                restart_program()
            elif exception_count >= RESTART_EXCEPTION_COUNT:
                print(f'>>>> Exception reach {RESTART_EXCEPTION_COUNT}, try to restart program!')
                restart_program()

            page_count += 1
            url = f.readline().strip()
            if str(url) == '':
                print('>>>> All Complaints Crawling Completed!')
                break

            print('\n>> Complaint {}, URL: {}'.format(page_count, url))
            if url in crawled_urls:
                print('Skip Crawled Url')
                continue
            try:
                time.sleep(SLEEP_NEXT_COMPLAINT)
                complaint = getComplaintDetail(url, driver)
                print(complaint)
                complaints.append({'url': url, **complaint})
                # if page_count % 2 == 0:
                #     raise TimeoutException
            except Exception as e:
                print('>> Got Exception: {}'.format(traceback.format_exc()))
                exception_count += 1
                if type(e) == TimeoutException:
                    timeout_exception_count += 1

            complaint_count = len(complaints)
            if complaint_count == SAVE_COMPAINT_BATCH:
                print('>> Writing {} complaints to mongo...'.format(complaint_count))
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