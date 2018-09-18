# from gevent import monkey
# monkey.patch_all()
# from gevent import spawn, joinall
import multiprocessing as mp

import os, sys
import numpy as np
from driver import getChrome
from conf import ACCOUNT, PWD, IMPLICIT_WAIT_DRIVER, SLEEP_NEXT_COMPLAINTS_PAGE, SLEEP_NEXT_COMPLAINT, \
                 RETRY_COMPLAINT_DETAIL_TIMEOUT_COUNT, RESTART_EXCEPTION_COUNT, RESTART_TIMEOUT_EXCEPTION_COUNT,\
                 SAVE_COMPAINT_BATCH, N_WORKER
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
        print(f'>>>> Page: {page_count}')
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

def getComplaintDetail(url, driver, driver_no, retry=0):
    try:
        driver.get(url)
    except TimeoutException as e: # selenium exception type
        if retry >= RETRY_COMPLAINT_DETAIL_TIMEOUT_COUNT:
            print(f'[{driver_no}] >>>> TimeoutException still occurs in {retry} Retries, Raise...')
            raise(e)
        else:
            retry += 1
            print(f'[{driver_no}] >>>> Timeout, retrying {retry}...')
            # driver = getChrome(headless=True)
            # login(driver)
            return getComplaintDetail(url, driver, driver_no, retry)

    try:
        title = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[1]/div[2]/h2').text
    except:
        title = '' # not necessary

    print(f'[{driver_no}] >>>> Begin extractReporters')
    reporters, actual_reporter_count = extractReporters(driver)
    print(f'[{driver_no}] >>>> Begin extractReports')
    reports = extractReports(driver, reporters)
    print(f'[{driver_no}] >>>> Begin extractRumor')
    rumor = extractRumor(driver)
    print(f'[{driver_no}] >>>> Begin extractOfficial')
    official = extractOfficial(driver)
    print(f'[{driver_no}] >>>> Begin extractLooks')
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

def getDriver():
    driver = getChrome(headless=True)
    login(driver)
    return driver

def getComplaintDetails(urls, driver_no):
    driver = getDriver()
    print(f'[{driver_no}] >> Begin Crawling Complaint Details for {len(urls)} pages...')

    # TODO: reduce waiting time: {method 'recv_into' of '_socket.socket' objects}

    mongo = MongoHelper()
    complaints = []
    exception_count = 0
    timeout_exception_count = 0
    page_count = 0
    for url in urls:
        # restart when come across too many timeouts
        if timeout_exception_count >= RESTART_TIMEOUT_EXCEPTION_COUNT:
            print(f'[{driver_no}] >> Timeout Excepiton reach {RESTART_EXCEPTION_COUNT}, trying to restart program!')
            restart_program()
        elif exception_count >= RESTART_EXCEPTION_COUNT:
            print(f'[{driver_no}] >> Exception reach {RESTART_EXCEPTION_COUNT}, trying to restart program!')
            restart_program()

        page_count += 1
        print(f'\n[{driver_no}] >>>> Complaint {page_count}, URL: {url}')
        try:
            time.sleep(SLEEP_NEXT_COMPLAINT)
            complaint = getComplaintDetail(url, driver, driver_no)
            print(complaint)
            complaints.append({'url': url, **complaint})
        except Exception as e:
            print(f'[{driver_no}] >>>> Got Exception: {traceback.format_exc()}, URL: {url}')
            exception_count += 1
            if type(e) == TimeoutException:
                timeout_exception_count += 1

        complaint_count = len(complaints)
        if complaint_count == SAVE_COMPAINT_BATCH:
            print(f'\n[{driver_no}] >> Writing {complaint_count} complaints to mongo...')
            mongo.update(complaints)
            complaints = []

    # update remaining results
    if len(complaints) != 0:
        mongo.update(complaints)
        print(f'\n[{driver_no}] >> Writing {len(complaints)} complaints to mongo...')
    else:
        pass
    print(f'[{driver_no}] >> All Complaints Crawling Completed!')

def getComplaintDetailsMultiWorker(n_worker):
    with open('complaint_urls.txt') as f:
        urls = f.read().split('\n')
    mongo = MongoHelper()
    crawled_urls = mongo.getCrawledUrls()
    todo_urls = [url for url in urls if url not in crawled_urls]
    print(f'>> {len(crawled_urls)}/{len(urls)} urls has been crawled, remain: {len(todo_urls)}')
    todo_urls_list = np.array_split(todo_urls, n_worker)

    # Concurrent
    # joinall([spawn(getComplaintDetails, urls, i) for i, urls in enumerate(urls_list)])
    pool = mp.Pool(n_worker)
    # Create post object
    jobs = [pool.apply_async(getComplaintDetails, (urls, i)) for i, urls in enumerate(todo_urls_list)]
    return [job.get() for job in jobs]


if __name__ == '__main__':
    # getComplaintUrls(driver)
    import cProfile
    cProfile.run(f'getComplaintDetailsMultiWorker({N_WORKER})')