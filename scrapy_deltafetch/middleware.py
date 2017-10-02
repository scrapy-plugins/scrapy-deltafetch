#-*- coding: utf-8 -*-

"""Scrapy Delta Fetch"""

import logging
import os
import time

from scrapy.http import Request
from scrapy.item import BaseItem
from scrapy.utils.request import request_fingerprint
from scrapy.utils.project import data_path
from scrapy.utils.python import to_bytes
from scrapy.exceptions import NotConfigured
from scrapy import signals


logger = logging.getLogger(__name__)

class DeltaFetch(object):
    """
    This is a spider middleware to ignore requests to pages containing items
    seen in previous crawls of the same spider, thus producing a "delta crawl"
    containing only new items.

    This also speeds up the crawl, by reducing the number of requests that need
    to be crawled, and processed (typically, item requests are the most cpu
    intensive).
    """

    def __init__(self, directory, reset=False, stats=None):
        dbmodule = None
        try:
            dbmodule = __import__('bsddb3').db
        except ImportError:
            raise NotConfigured('bsddb3 is required')
        self.dbmodule = dbmodule
        self.database = None
        self.directory = directory
        self.reset = reset
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """Load middleware settings and setup signals"""
        settings = crawler.settings
        if not settings.getbool('DELTAFETCH_ENABLED'):
            raise NotConfigured
        directory = data_path(settings.get('DELTAFETCH_DIR', 'deltafetch'))
        reset = settings.getbool('DELTAFETCH_RESET')
        middleware = cls(directory, reset, crawler.stats)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider):
        """Create database if it doesn't exist and open the handle"""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        dbpath = os.path.join(self.directory, '%s.db' % spider.name)
        reset = self.reset or getattr(spider, 'deltafetch_reset', False)
        flag = self.dbmodule.DB_TRUNCATE if reset else self.dbmodule.DB_CREATE
        try:
            self.database = self.dbmodule.DB()
            self.database.open(
                filename=dbpath,
                dbtype=self.dbmodule.DB_HASH,
                flags=flag
            )
        except self.dbmodule.DBError:
            logger.warning(
                "Failed to open DeltaFetch database at %s, trying to recreate it",
                dbpath
            )
            if os.path.exists(dbpath):
                os.remove(dbpath)
            self.database = self.dbmodule.DB()
            self.database.open(
                filename=dbpath,
                dbtype=self.dbmodule.DB_HASH,
                flags=self.dbmodule.DB_CREATE
            )

    def spider_closed(self, spider):
        """Close the database handle"""
        if self.database:
            self.database.close()

    def process_spider_output(self, response, result, spider):
        """Retrieve key, lookup database and skip request if key exists"""
        for each in result:
            if isinstance(each, Request):
                key = self._get_key(each)
                if key in self.database:
                    logger.info("Ignoring already visited: %s", each)
                    if self.stats:
                        self.stats.inc_value('deltafetch/skipped', spider=spider)
                    continue
            elif isinstance(each, (BaseItem, dict)):
                key = self._get_key(response.request)
                self.database[key] = str(time.time())
                if self.stats:
                    self.stats.inc_value('deltafetch/stored', spider=spider)
            yield each

    @staticmethod
    def _get_key(request):
        """Retrieve key to use for database lookup"""
        key = request.meta.get('deltafetch_key') or request_fingerprint(request)
        return to_bytes(key)
