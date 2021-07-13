from unittest import TestCase, skipIf

import os
import mock
import tempfile
from scrapy import Request
from scrapy.item import Item
from scrapy.spiders import Spider
from scrapy.settings import Settings
from scrapy.exceptions import NotConfigured
from scrapy.utils.request import request_fingerprint
from scrapy.utils.python import to_bytes
from scrapy.statscollectors import StatsCollector
from scrapy.utils.test import get_crawler

from scrapy_deltafetch.middleware import DeltaFetch


dbmodule = None
try:
    dbmodule = __import__('bsddb3')
except ImportError:
    pass


@skipIf(not dbmodule, "bsddb3 is not found on the system")
class DeltaFetchTestCase(TestCase):

    mwcls = DeltaFetch

    def setUp(self):
        self.spider_name = 'df_tests'
        self.spider = Spider(self.spider_name)

        # DeltaFetch creates .db files named after the spider's name
        self.temp_dir = tempfile.gettempdir()
        self.db_path = os.path.join(self.temp_dir, '%s.db' % self.spider.name)

        crawler = get_crawler(Spider)
        self.stats = StatsCollector(crawler)

    def test_init(self):
        # path format is any,  the folder is not created
        instance = self.mwcls('/any/dir', True, stats=self.stats)
        assert isinstance(instance, self.mwcls)
        self.assertEqual(instance.dir, '/any/dir')
        self.assertEqual(self.stats.get_stats(), {})
        self.assertEqual(instance.reset, True)

    def test_init_from_crawler(self):
        crawler = mock.Mock()
        # void settings
        crawler.settings = Settings({})
        self.assertRaises(NotConfigured, self.mwcls.from_crawler, crawler)
        with mock.patch('scrapy.utils.project.project_data_dir') as data_dir, \
             mock.patch('scrapy.utils.project.inside_project') as in_project:
            data_dir.return_value = self.temp_dir
            in_project.return_value = True

            # simple project_data_dir mock with based settings
            crawler.settings = Settings({'DELTAFETCH_ENABLED': True})
            instance = self.mwcls.from_crawler(crawler)
            assert isinstance(instance, self.mwcls)
            self.assertEqual(
                instance.dir, os.path.join(self.temp_dir, 'deltafetch'))
            self.assertEqual(instance.reset, False)

            # project_data_dir mock with advanced settings
            crawler.settings = Settings({'DELTAFETCH_ENABLED': True,
                                         'DELTAFETCH_DIR': 'other',
                                         'DELTAFETCH_RESET': True})
            instance = self.mwcls.from_crawler(crawler)
            assert isinstance(instance, self.mwcls)
            self.assertEqual(
                instance.dir, os.path.join(self.temp_dir, 'other'))
            self.assertEqual(instance.reset, True)

    def test_spider_opened_new(self):
        """Middleware should create a .db file if not found."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        assert not hasattr(self.mwcls, 'db')
        mw.spider_opened(self.spider)
        assert os.path.isdir(self.temp_dir)
        assert os.path.exists(self.db_path)
        assert hasattr(mw, 'db')
        assert isinstance(mw.db, type(dbmodule.db.DB()))
        assert mw.db.items() == []
        assert mw.db.get_type() == dbmodule.db.DB_HASH
        assert mw.db.get_open_flags() == dbmodule.db.DB_CREATE

    def test_spider_opened_existing(self):
        """Middleware should open and use existing and valid .db files."""
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        assert not hasattr(self.mwcls, 'db')
        mw.spider_opened(self.spider)
        assert hasattr(mw, 'db')
        assert isinstance(mw.db, type(dbmodule.db.DB()))
        assert mw.db.items() == [(b'test_key_1', b'test_v_1'),
                                 (b'test_key_2', b'test_v_2')]
        assert mw.db.get_type() == dbmodule.db.DB_HASH
        assert mw.db.get_open_flags() == dbmodule.db.DB_CREATE

    def test_spider_opened_corrupt_dbfile(self):
        """Middleware should create a new .db if it cannot open it."""
        # create an invalid .db file
        with open(self.db_path, "wb") as dbfile:
            dbfile.write(b'bad')
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        assert not hasattr(self.mwcls, 'db')

        # file corruption is only detected when opening spider
        mw.spider_opened(self.spider)
        assert os.path.isdir(self.temp_dir)
        assert os.path.exists(self.db_path)
        assert hasattr(mw, 'db')
        assert isinstance(mw.db, type(dbmodule.db.DB()))

        # and db should be empty (it was re-created)
        assert mw.db.items() == []
        assert mw.db.get_type() == dbmodule.db.DB_HASH
        assert mw.db.get_open_flags() == dbmodule.db.DB_CREATE

    def test_spider_opened_existing_spider_reset(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        assert not hasattr(self.mwcls, 'db')
        self.spider.deltafetch_reset = True
        mw.spider_opened(self.spider)
        assert mw.db.get_open_flags() == dbmodule.db.DB_TRUNCATE

    def test_spider_opened_reset_non_existing_db(self):
        mw = self.mwcls(self.temp_dir, reset=True, stats=self.stats)
        assert not hasattr(self.mwcls, 'db')
        self.spider.deltafetch_reset = True
        mw.spider_opened(self.spider)
        assert mw.db.fd()
        # there's different logic for different bdb versions:
        # it can fail when opening a non-existing db with truncate flag,
        # then it should be caught and retried with rm & create flag
        assert (mw.db.get_open_flags() == dbmodule.db.DB_CREATE or
                mw.db.get_open_flags() == dbmodule.db.DB_TRUNCATE)

    def test_spider_opened_recreate(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=True, stats=self.stats)
        assert not hasattr(self.mwcls, 'db')
        mw.spider_opened(self.spider)
        assert hasattr(mw, 'db')
        assert isinstance(mw.db, type(dbmodule.db.DB()))
        assert mw.db.items() == []
        assert mw.db.get_type() == dbmodule.db.DB_HASH
        assert mw.db.get_open_flags() == dbmodule.db.DB_TRUNCATE

    def test_spider_closed(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=True, stats=self.stats)
        mw.spider_opened(self.spider)
        assert mw.db.fd()
        mw.spider_closed(self.spider)
        self.assertRaises(dbmodule.db.DBError, mw.db.fd)

    def test_process_spider_output(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        mw.spider_opened(self.spider)
        response = mock.Mock()
        response.request = Request('http://url',
                                   meta={'deltafetch_key': 'key'})
        result = []
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), [])
        result = [
            # same URL but with new key --> it should be processed
            Request('http://url', meta={'deltafetch_key': 'key1'}),

            # 'test_key_1' is already in the test db --> it should be skipped
            Request('http://url1', meta={'deltafetch_key': 'test_key_1'})
        ]
        # so only the 1 request should go through
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), [result[0]])

        # the skipped "http://url1" should be counted in stats
        self.assertEqual(self.stats.get_stats(), {'deltafetch/skipped': 1})

        # b'key' should not be in the db yet as no item was collected yet
        self.assertEqual(set(mw.db.keys()),
                         set([b'test_key_1',
                              b'test_key_2']))

        # if the spider returns items, the request's key is added in db
        result = [Item(), "not a base item"]
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), result)
        self.assertEqual(set(mw.db.keys()),
                         set([b'key',
                              b'test_key_1',
                              b'test_key_2']))
        assert mw.db[b'key']

    def test_process_spider_output_with_ignored_request(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        mw.spider_opened(self.spider)
        response = mock.Mock()
        response.request = Request('http://url')
        result = []
        self.assertEqual(
            list(mw.process_spider_output(response, result, self.spider)), [])
        result = [
            # same URL but with new key --> it should be processed
            Request('http://url', meta={'deltafetch_ignore': True}),

            # 'test_key_1' is already in the test db, but deltafetch_ignore
            # flag is set --> it should be processed
            Request('http://url1',
                    meta={
                        'deltafetch_key': 'test_key_1',
                        'deltafetch_ignore': True
                    })
        ]
        # so 2 requests should go through
        self.assertEqual(
            list(mw.process_spider_output(response, result, self.spider)),
            [result[0], result[1]])

    def test_process_spider_output_dict(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        mw.spider_opened(self.spider)
        response = mock.Mock()
        response.request = Request('http://url',
                                   meta={'deltafetch_key': 'key'})
        result = [{"somekey": "somevalue"}]
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), result)
        self.assertEqual(set(mw.db.keys()),
                         set([b'key',
                              b'test_key_1',
                              b'test_key_2']))
        assert mw.db[b'key']

    def test_process_spider_output_stats(self):
        self._create_test_db()
        mw = self.mwcls(self.temp_dir, reset=False, stats=self.stats)
        mw.spider_opened(self.spider)
        response = mock.Mock()
        response.request = Request('http://url',
                                   meta={'deltafetch_key': 'key'})
        result = []
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), [])
        self.assertEqual(self.stats.get_stats(), {})
        result = [
            Request('http://url', meta={'deltafetch_key': 'key'}),
            Request('http://url1', meta={'deltafetch_key': 'test_key_1'})
        ]
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), [result[0]])
        self.assertEqual(self.stats.get_value('deltafetch/skipped'), 1)
        result = [Item(), "not a base item"]
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), result)
        self.assertEqual(self.stats.get_value('deltafetch/stored'), 1)

    def test_init_from_crawler_legacy(self):
        # test with subclass not handling passed stats
        class LegacyDeltaFetchSubClass(self.mwcls):

            def __init__(self, dir, reset=False, *args, **kwargs):
                super(LegacyDeltaFetchSubClass, self).__init__(dir=dir, reset=reset)
                self.something = True

        crawler = mock.Mock()
        # void settings
        crawler.settings = Settings({})
        self.assertRaises(NotConfigured, self.mwcls.from_crawler, crawler)

        with mock.patch('scrapy.utils.project.project_data_dir') as data_dir, \
             mock.patch('scrapy.utils.project.inside_project') as in_project:
            data_dir.return_value = self.temp_dir
            in_project.return_value = True

            # simple project_data_dir mock with based settings
            crawler.settings = Settings({'DELTAFETCH_ENABLED': True})
            instance = LegacyDeltaFetchSubClass.from_crawler(crawler)
            assert isinstance(instance, self.mwcls)
            self.assertEqual(
                instance.dir, os.path.join(self.temp_dir, 'deltafetch'))
            self.assertEqual(instance.reset, False)

            # project_data_dir mock with advanced settings
            crawler.settings = Settings({'DELTAFETCH_ENABLED': True,
                                         'DELTAFETCH_DIR': 'other',
                                         'DELTAFETCH_RESET': True})
            instance = LegacyDeltaFetchSubClass.from_crawler(crawler)
            assert isinstance(instance, self.mwcls)
            self.assertEqual(
                instance.dir, os.path.join(self.temp_dir, 'other'))
            self.assertEqual(instance.reset, True)

    def test_process_spider_output_stats_legacy(self):
        # testing the subclass not handling stats works at runtime
        # (i.e. that trying to update stats does not trigger exception)
        class LegacyDeltaFetchSubClass(self.mwcls):

            def __init__(self, dir, reset=False, *args, **kwargs):
                super(LegacyDeltaFetchSubClass, self).__init__(dir=dir, reset=reset)
                self.something = True

        self._create_test_db()
        mw = LegacyDeltaFetchSubClass(self.temp_dir, reset=False)
        mw.spider_opened(self.spider)
        response = mock.Mock()
        response.request = Request('http://url',
                                   meta={'deltafetch_key': 'key'})
        result = []
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), [])
        self.assertEqual(self.stats.get_stats(), {})
        result = [
            Request('http://url', meta={'deltafetch_key': 'key'}),
            Request('http://url1', meta={'deltafetch_key': 'test_key_1'})
        ]

        # stats should not be updated
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), [result[0]])
        self.assertEqual(self.stats.get_value('deltafetch/skipped'), None)

        result = [Item(), "not a base item"]
        self.assertEqual(list(mw.process_spider_output(
            response, result, self.spider)), result)
        self.assertEqual(self.stats.get_value('deltafetch/stored'), None)

    def test_get_key(self):
        mw = self.mwcls(self.temp_dir, reset=True)
        test_req1 = Request('http://url1')
        self.assertEqual(mw._get_key(test_req1),
                         to_bytes(request_fingerprint(test_req1)))
        test_req2 = Request('http://url2', meta={'deltafetch_key': b'dfkey1'})
        self.assertEqual(mw._get_key(test_req2), b'dfkey1')

        test_req3 = Request('http://url2', meta={'deltafetch_key': u'dfkey1'})
        # key will be converted to bytes
        self.assertEqual(mw._get_key(test_req3), b'dfkey1')

    def _create_test_db(self):
        db = dbmodule.db.DB()
        # truncate test db if there were failed tests
        db.open(self.db_path, dbmodule.db.DB_HASH,
                dbmodule.db.DB_CREATE | dbmodule.db.DB_TRUNCATE)
        db[b'test_key_1'] = b'test_v_1'
        db[b'test_key_2'] = b'test_v_2'
        db.close()
