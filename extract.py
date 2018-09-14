import traceback
import time
import re
from selenium.common.exceptions import StaleElementReferenceException

def extractReporter(driver):
    reporter = driver.find_element_by_xpath(
        '//div[@class="W_main_half_l"]//div[@class="user bg_blue2 clearfix"]')
    reporter_name = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').text
    reporter_url = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').get_attribute('href')
    reporter_img_url = reporter.find_element_by_xpath(
        '//*[@id="pl_service_common"]/div[2]/div[1]/div/div[2]/div/img').get_attribute('src')
    reporter_gender = reporter.find_element_by_xpath('p[@class="mb"]/img').get_attribute('class')
    reporter_location = reporter.find_element_by_xpath('p[@class="mb"]').text
    reporter_description = reporter.find_element_by_xpath('p[last()]').text

    return {'reporter_url': reporter_url,
            'reporter_name': reporter_name,
            'reporter_img_url': reporter_img_url,
            'reporter_gender': reporter_gender,
            'reporter_location': reporter_location,
            'reporter_description': reporter_description,
            }

def extractReporters(driver):
    reporter_count_text = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[2]/div[1]/div/div[1]/span[2]').text
    if re.match('\(共有', reporter_count_text):
        reporter_count = 20
        actual_reporter_count = int(reporter_count_text.split(sep='共有')[1].split(sep='人')[0])
    else:
        reporter_count = int(reporter_count_text.split(sep='共')[1].split(sep='人')[0])
        actual_reporter_count = reporter_count
    print('Reporter Count: {}, Actual: {}'.format(reporter_count, actual_reporter_count))

    if reporter_count == 1:
        crawled_reporters = [extractReporter(driver)]
    else:
        iter = 0
        crawled_reporters = []
        crawled_reporter_names = []
        while True:
            iter += 1
            print('reporter iter: {}'.format(iter))
            if len(crawled_reporter_names) == reporter_count:
                break

            try:  # StaleElementReferenceException, if no try, will throw not-attached element exception
                reporter = driver.find_element_by_xpath(
                    '//div[@class="W_main_half_l"]//div[@class="user bg_blue2 clearfix"]')
                reporter_name = reporter.find_element_by_xpath('p[@class="mb W_f14"]/a[1]').text

                if reporter_name not in crawled_reporter_names:
                    crawled_reporters.append(extractReporter(driver))
                    crawled_reporter_names.append(reporter_name)
                else:
                    print('duplicated reporter')

                next_reporter = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[2]/div[1]/div/div[1]/a')
                next_reporter.click()
                time.sleep(0.5)

            except:
                print('Reporter iter exception: {}'.format(traceback.format_exc()))
                continue

    return crawled_reporters, actual_reporter_count

def extractReports(driver, crawled_reporters):
    crawled_reports_count = 0
    while True:
        reports = driver.find_elements_by_xpath('//*[@id="pl_service_common"]/div[4]/div[1]/div/div/div[1]/div')
        for report in reports:
            report_time_text = report.find_element_by_xpath('p[@class="publisher"]').text
            if report_time_text != '举报人：':
                report_time = report_time_text.split('举报人陈述时间：')[1]
                report_text = report.find_element_by_xpath('div[@class="feed clearfix"]/div[@class="con"]').text
                reporter_url = report.find_element_by_xpath(
                    'div[@class="feed clearfix"]/div[@class="con"]/a').get_attribute('href')
                for r in crawled_reporters:
                    if r['reporter_url'] == reporter_url:
                        r['report_time'] = report_time
                        r['report_text'] = report_text
                    else:
                        pass
            else:
                print('Reporter deleted report')
                pass
        crawled_reports_count += len(reports)
        print('crawled reporters: {}, crawled reports: {}'.format(len(crawled_reporters), crawled_reports_count))

        try:
            next_page = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[4]/div[1]/div/div/div[2]/div/a[@class="next"]')
            next_page.click()
            time.sleep(0.5)
            print('Go to next reports page')
        except:
            break

    return crawled_reporters

def extractRumor(driver):
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

    rumor = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[4]/div[2]/div/div/div/div')
    # TODO: handle deleted rumor weibo
    rumor_time_text = rumor.find_element_by_xpath('p[@class="publisher"]').text
    if rumor_time_text != '被举报微博':
        rumor_time = rumor_time_text.split('被举报微博 发布时间：')[1].split(' | 原文')[0]

        try:
            rumor_url = rumor.find_element_by_xpath('p[@class="publisher"]/a').get_attribute('href')
        except:
            print('Can not find original url of rumor')
            rumor_url = ''

        rumor_text = rumor.find_element_by_xpath('div[@class="feed bg_orange2 clearfix"]/div[@class="con"]').text
        rumorer_url = rumor.find_element_by_xpath(
            'div[@class="feed bg_orange2 clearfix"]/div[@class="con"]/a').get_attribute('href')
        assert rumorer_url == crawled_rumor['rumorer_url']
        crawled_rumor['rumor_url'] = rumor_url
        crawled_rumor['rumor_time'] = rumor_time
        crawled_rumor['rumor_text'] = rumor_text
    else:
        print('Rumor weibo deleted')
        pass

    return crawled_rumor

def extractOfficial(driver):
    official_text = driver.find_element_by_xpath('//*[@id="pl_service_common"]/div[3]/div/div/p').text
    crawled_official = {
        'official_text': official_text
    }
    return crawled_official

def extractLooks(driver):
    crawled_looks = []
    for look in driver.find_elements_by_xpath('//*[@id="pl_service_looker"]/div/ul/li'):
        looker_url = look.find_element_by_xpath('a').get_attribute('href')
        looker_name = look.find_element_by_xpath('a').get_attribute('title')
        crawled_looks.append([looker_url, looker_name])
    return crawled_looks