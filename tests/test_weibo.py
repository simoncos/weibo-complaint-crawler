import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import weibo


class FakeLink:
    def __init__(self, href=None, text='', attributes=None, on_click=None):
        self.text = text
        self._attributes = dict(attributes or {})
        if href is not None:
            self._attributes['href'] = href
        self._on_click = on_click

    def get_attribute(self, name):
        return self._attributes.get(name)

    def click(self):
        if self._on_click is not None:
            self._on_click()


class FakeRow:
    def __init__(self, url):
        self.link = FakeLink(href=url)

    def find_element_by_xpath(self, xpath):
        return self.link


class FakeListDriver:
    def __init__(self, pages):
        self.pages = pages
        self.page_index = 0
        self.visited = []

    def get(self, url):
        self.visited.append(url)

    def find_elements_by_xpath(self, xpath):
        page = self.pages[self.page_index]
        if 'tbody/tr' in xpath:
            return [FakeRow(url) for url in page['urls']]
        if 'W_btn_c' in xpath:
            controls = []
            for label, target in page.get('controls', []):
                controls.append(FakeLink(
                    text=label,
                    on_click=lambda target=target: setattr(self, 'page_index', target)))
            return controls
        raise AssertionError('Unexpected xpath: {}'.format(xpath))


class FakeWorkerDriver:
    def __init__(self, name, events):
        self.name = name
        self.events = events

    def quit(self):
        self.events.append(('quit', self.name))


class FakeMongo:
    def __init__(self, events):
        self.events = events
        self.updates = []

    def update(self, records):
        snapshot = [dict(record) for record in records]
        self.updates.append(snapshot)
        self.events.append(('update', [record['url'] for record in snapshot]))


class UrlCheckpointTests(unittest.TestCase):
    def test_checkpoint_filters_blanks_and_stably_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'complaint_urls.txt'
            checkpoint.write_text('url-b\n\nurl-a\nurl-b\n  url-a  \n')

            self.assertEqual(
                weibo._read_url_checkpoint(str(checkpoint)),
                ['url-b', 'url-a'])

            weibo._write_url_checkpoint(
                ['url-b', '', 'url-a', 'url-b'], str(checkpoint))
            self.assertEqual(checkpoint.read_text(), 'url-b\nurl-a\n')

    def test_last_page_is_saved_and_previous_control_is_not_clicked(self):
        driver = FakeListDriver([
            {'urls': ['url-1'], 'controls': [('下一页', 1)]},
            {'urls': ['url-2'], 'controls': [('上一页', 0)]},
        ])
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'complaint_urls.txt'
            result = weibo.getComplaintUrls(
                driver, str(checkpoint), sleep_fn=lambda _: None)

            self.assertEqual(result, ['url-1', 'url-2'])
            self.assertEqual(checkpoint.read_text(), 'url-1\nurl-2\n')
            self.assertEqual(driver.page_index, 1)

    def test_single_page_without_controls_is_checkpointed(self):
        driver = FakeListDriver([
            {'urls': ['only-url'], 'controls': []},
        ])
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'complaint_urls.txt'
            result = weibo.getComplaintUrls(
                driver, str(checkpoint), sleep_fn=lambda _: None)

            self.assertEqual(result, ['only-url'])
            self.assertEqual(checkpoint.read_text(), 'only-url\n')

    def test_repeated_page_guard_stops_a_next_page_cycle(self):
        driver = FakeListDriver([
            {'urls': ['url-1'], 'controls': [('下一页', 1)]},
            {'urls': ['url-2'], 'controls': [('下一页', 0)]},
        ])
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'complaint_urls.txt'
            result = weibo.getComplaintUrls(
                driver, str(checkpoint), sleep_fn=lambda _: None)

            self.assertEqual(result, ['url-1', 'url-2'])
            self.assertEqual(checkpoint.read_text(), 'url-1\nurl-2\n')


class WorkerRecoveryTests(unittest.TestCase):
    def test_recycle_flushes_batch_without_restarting_entry_or_logging_payload(self):
        events = []
        mongo = FakeMongo(events)
        drivers = []

        def make_driver(driver, driver_no):
            worker_driver = FakeWorkerDriver('driver-{}'.format(len(drivers) + 1), events)
            drivers.append(worker_driver)
            events.append(('driver', worker_driver.name))
            return worker_driver

        def extract(url, driver, driver_no):
            if url == 'url-fails':
                raise RuntimeError('synthetic parse failure')
            return {'private_marker': 'DO_NOT_LOG_THIS_RECORD'}

        output = io.StringIO()
        with mock.patch.object(weibo, 'MongoHelper', return_value=mongo), \
                mock.patch.object(weibo, 'getDriver', side_effect=make_driver), \
                mock.patch.object(weibo, 'login', side_effect=lambda driver: events.append(('login', driver.name))), \
                mock.patch.object(weibo, 'getComplaintDetail', side_effect=extract), \
                mock.patch.object(weibo.time, 'sleep', return_value=None), \
                mock.patch.object(weibo, 'RESTART_EXCEPTION_COUNT', 1), \
                mock.patch.object(weibo, 'RESTART_TIMEOUT_EXCEPTION_COUNT', 99), \
                mock.patch.object(weibo, 'SAVE_COMPAINT_BATCH', 10), \
                contextlib.redirect_stdout(output):
            weibo.getComplaintDetails(
                ['url-before-recycle', 'url-fails', 'url-after-recycle'], 0)

        self.assertEqual(len(drivers), 2)
        self.assertEqual(
            [[record['url'] for record in batch] for batch in mongo.updates],
            [['url-before-recycle'], ['url-after-recycle']])
        self.assertLess(
            events.index(('update', ['url-before-recycle'])),
            events.index(('driver', 'driver-2')))
        self.assertEqual(
            [event for event in events if event[0] == 'quit'],
            [('quit', 'driver-1'), ('quit', 'driver-2')])
        self.assertNotIn('DO_NOT_LOG_THIS_RECORD', output.getvalue())


if __name__ == '__main__':
    unittest.main()
