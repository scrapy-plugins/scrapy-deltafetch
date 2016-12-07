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

    def __init__(self, dir, reset=False, stats=None):
        dbmodule = None
        try:
            dbmodule = __import__('bsddb3').db
        except ImportError:
            raise NotConfigured('bsddb3 is required')
        self.dbmodule = dbmodule
        self.dir = dir
        self.reset = reset
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        s = crawler.settings
        if not s.getbool('DELTAFETCH_ENABLED'):
            raise NotConfigured
        dir = data_path(s.get('DELTAFETCH_DIR', 'deltafetch'))
        reset = s.getbool('DELTAFETCH_RESET')
        o = cls(dir, reset, crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        dbpath = os.path.join(self.dir, '%s.db' % spider.name)
        reset = self.reset or getattr(spider, 'deltafetch_reset', False)
        flag = self.dbmodule.DB_TRUNCATE if reset else self.dbmodule.DB_CREATE
        try:
            self.db = self.dbmodule.DB()
            self.db.open(filename=dbpath,
                         dbtype=self.dbmodule.DB_HASH,
                         flags=flag)
        except Exception:
            logger.warning("Failed to open DeltaFetch database at %s, "
                           "trying to recreate it" % dbpath)
            if os.path.exists(dbpath):
                os.remove(dbpath)
            self.db = self.dbmodule.DB()
            self.db.open(filename=dbpath,
                         dbtype=self.dbmodule.DB_HASH,
                         flags=self.dbmodule.DB_CREATE)

    def spider_closed(self, spider):
        self.db.close()

    def process_spider_output(self, response, result, spider):
        for r in result:
            if isinstance(r, Request):
                key = self._get_key(r)
                if key in self.db:
                    logger.info("Ignoring already visited: %s" % r)
                    if self.stats:
                        self.stats.inc_value('deltafetch/skipped', spider=spider)
                    continue
            elif isinstance(r, (BaseItem, dict)):
                key = self._get_key(response.request)
                self.db[key] = str(time.time())
                if self.stats:
                    self.stats.inc_value('deltafetch/stored', spider=spider)
            yield r

    def _get_key(self, request):
        key = request.meta.get('deltafetch_key') or request_fingerprint(request)
        # request_fingerprint() returns `hashlib.sha1().hexdigest()`, is a string
        return to_bytes(key)
