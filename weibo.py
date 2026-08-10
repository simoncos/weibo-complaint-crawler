# from gevent import monkey
# monkey.patch_all()
# from gevent import spawn, joinall
import multiprocessing as mp

import os
import tempfile
import numpy as np
try:
    from driver import getDriver
except ImportError:  # Allow the offline tests to run without browser packages.
    getDriver = None
from conf import ACCOUNT, PWD, IMPLICIT_WAIT_DRIVER, SLEEP_NEXT_COMPLAINTS_PAGE, SLEEP_NEXT_COMPLAINT, \
                 RETRY_COMPLAINT_DETAIL_TIMEOUT_COUNT, RESTART_EXCEPTION_COUNT, RESTART_TIMEOUT_EXCEPTION_COUNT,\
                 SAVE_COMPAINT_BATCH, N_WORKER, WEB_DRIVER
try:
    from mongo import MongoHelper
except ImportError:  # Allow the offline tests to run without a Mongo client.
    MongoHelper = None
from extract import *
try:
    from selenium.common.exceptions import TimeoutException
except ImportError:
    class TimeoutException(Exception):
        """Offline fallback used only when Selenium is not installed."""

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

def _stable_unique_urls(urls):
    """Return non-empty URLs once, preserving their first-seen order."""
    result = []
    seen = set()
    for raw_url in urls:
        url = raw_url.strip()
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _read_url_checkpoint(path='complaint_urls.txt'):
    try:
        with open(path) as checkpoint:
            return _stable_unique_urls(checkpoint)
    except FileNotFoundError:
        return []


def _write_url_checkpoint(urls, path='complaint_urls.txt'):
    """Atomically replace the checkpoint with a de-duplicated URL manifest."""
    urls = _stable_unique_urls(urls)
    checkpoint_dir = os.path.dirname(os.path.abspath(path))
    fd, temporary_path = tempfile.mkstemp(
        prefix='.complaint_urls.', suffix='.tmp', dir=checkpoint_dir, text=True)
    try:
        with os.fdopen(fd, 'w') as checkpoint:
            if urls:
                checkpoint.write('\n'.join(urls) + '\n')
        os.replace(temporary_path, path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def _find_next_complaints_page(driver):
    """Find a control that explicitly identifies itself as the next page."""
    candidates = driver.find_elements_by_xpath('//a[contains(@class, "W_btn_c")]')
    for candidate in candidates:
        label = (getattr(candidate, 'text', '') or '').strip().lower()
        rel = (candidate.get_attribute('rel') or '').strip().lower()
        title = (candidate.get_attribute('title') or '').strip().lower()
        if rel == 'next' or label in ('下一页', 'next') or title in ('下一页', 'next'):
            return candidate
    return None


def getComplaintUrls(driver, checkpoint_path='complaint_urls.txt', sleep_fn=time.sleep):

    # Enter http://service.account.weibo.com
    driver.get('http://service.account.weibo.com/?type=5&status=4')
    page_count = 1
    complaint_urls = _read_url_checkpoint(checkpoint_path)
    seen_urls = set(complaint_urls)
    seen_pages = set()
    print('>> Begin Crawling Complaint Urls...')
    while True:
        # Iterate list in each page
        print(f'>>>> Page: {page_count}')
        page_urls = []
        for info in driver.find_elements_by_xpath('//div[@id="pl_service_showcomplaint"]/table[@class="m_table"]'
                                                  '/tbody/tr[not(@class)]'):
            # print(info.text)
            # print(info.find_element_by_xpath('td[2]/div[@class="m_table_tit"]/a').get_attribute('href'),
            #       info.find_element_by_xpath('td[3]/a').text,
            #       info.find_element_by_xpath('td[4]/a').text,
            #       )
            # print(info.find_element_by_xpath('td[2]/div[@class="m_table_tit"]/a').get_attribute('href'))
            page_urls.append(info.find_element_by_xpath(
                'td[2]/div[@class="m_table_tit"]/a').get_attribute('href'))

        page_urls = _stable_unique_urls(page_urls)
        page_signature = tuple(page_urls)
        if page_signature in seen_pages:
            print('>>>> Repeated page detected; stopping pagination')
            break
        seen_pages.add(page_signature)

        for url in page_urls:
            if url not in seen_urls:
                seen_urls.add(url)
                complaint_urls.append(url)

        print('>>>> Writing to Files...')
        _write_url_checkpoint(complaint_urls, checkpoint_path)

        next_page = _find_next_complaints_page(driver)
        if next_page is None:
            print('Next page not found')
            break

        next_page.click()
        sleep_fn(SLEEP_NEXT_COMPLAINTS_PAGE)
        page_count += 1

    return complaint_urls

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

def _quit_driver(driver):
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        print('>>>> Driver shutdown failed')


def _new_logged_in_driver(driver_no):
    if getDriver is None:
        raise RuntimeError('Selenium is required for live crawling')
    driver = getDriver(driver=WEB_DRIVER, driver_no=driver_no)
    try:
        login(driver)
    except Exception:
        _quit_driver(driver)
        raise
    return driver


def _flush_complaints(mongo, complaints, driver_no):
    if not complaints:
        return
    complaint_count = len(complaints)
    mongo.update(complaints)
    complaints.clear()
    print(f'\n[{driver_no}] >> Wrote {complaint_count} complaints to mongo')

def getComplaintDetails(urls, driver_no):
    if MongoHelper is None:
        raise RuntimeError('PyMongo is required for live crawling')
    driver = None
    mongo = MongoHelper()
    complaints = []
    exception_count = 0
    timeout_exception_count = 0
    page_count = 0
    try:
        driver = _new_logged_in_driver(driver_no)
        print(f'[{driver_no}] >> Begin Crawling Complaint Details for {len(urls)} pages...')

        for url in urls:
            # Recycle only this worker's browser. Persist successful buffered
            # records first so recovery cannot discard the current checkpoint.
            if (timeout_exception_count >= RESTART_TIMEOUT_EXCEPTION_COUNT or
                    exception_count >= RESTART_EXCEPTION_COUNT):
                _flush_complaints(mongo, complaints, driver_no)
                _quit_driver(driver)
                driver = None
                print(f'[{driver_no}] >> Recycling browser after repeated exceptions')
                driver = _new_logged_in_driver(driver_no)
                exception_count = 0
                timeout_exception_count = 0

            page_count += 1
            print(f'\n[{driver_no}] >>>> Complaint {page_count}')
            try:
                time.sleep(SLEEP_NEXT_COMPLAINT)
                complaint = getComplaintDetail(url, driver, driver_no)
                complaints.append({'url': url, **complaint})
            except Exception as e:
                print(f'[{driver_no}] >>>> Got Exception: {traceback.format_exc()}')
                exception_count += 1
                if type(e) == TimeoutException:
                    timeout_exception_count += 1

            if len(complaints) >= SAVE_COMPAINT_BATCH:
                _flush_complaints(mongo, complaints, driver_no)

        _flush_complaints(mongo, complaints, driver_no)
        print(f'[{driver_no}] >> All Complaints Crawling Completed!')
    finally:
        _quit_driver(driver)

def getComplaintDetailsMultiWorker(n_worker):
    urls = _read_url_checkpoint('complaint_urls.txt')
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
