import os
import time
from logging import getLogger
from typing import Iterable

import bsddb3
from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.http import Request, Response
from scrapy.item import Item
from scrapy.spiders import Spider
from scrapy.statscollectors import StatsCollector
from scrapy.utils.project import data_path
from scrapy.utils.python import to_bytes
from scrapy.utils.request import request_fingerprint

logger = getLogger(__name__)


class DeltaFetch:
    """
    This is a spider middleware to ignore requests to pages containing items
    seen in previous crawls of the same spider, thus producing a "delta crawl"
    containing only new items.

    This also speeds up the crawl, by reducing the number of requests that need
    to be crawled, and processed (typically, item requests are the most cpu
    intensive).
    """

    def __init__(self, dir: str, reset: bool = False, stats: StatsCollector = None):
        self.dir = dir
        self.reset = reset
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        s = crawler.settings
        if not s.getbool("DELTAFETCH_ENABLED"):
            raise NotConfigured
        dir = data_path(s.get("DELTAFETCH_DIR", "deltafetch"))
        reset = s.getbool("DELTAFETCH_RESET")
        o = cls(dir, reset, crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider: Spider) -> None:
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)
        dbpath = os.path.join(self.dir, f"{spider.name}.db")
        reset = self.reset or getattr(spider, "deltafetch_reset", False)
        flag = bsddb3.db.DB_TRUNCATE if reset else bsddb3.db.DB_CREATE

        try:
            self.db = bsddb3.db.DB()
            self.db.open(filename=dbpath, dbtype=bsddb3.db.DB_HASH, flags=flag)
        except bsddb3.db.DBError:
            logger.warning(
                f"Failed to open DeltaFetch database at {dbpath}, trying to recreate it"
            )
            if os.path.isfile(dbpath):
                os.remove(dbpath)
            self.db = bsddb3.db.DB()
            self.db.open(
                filename=dbpath, dbtype=bsddb3.db.DB_HASH, flags=bsddb3.db.DB_CREATE,
            )

    def spider_closed(self, _spider: Spider) -> None:
        self.db.close()

    def process_spider_output(
        self, response: Response, result: Iterable, spider: Spider
    ):
        for r in result:
            if isinstance(r, Request):
                key = self._get_key(r)
                if key in self.db:
                    logger.info(f"Ignoring already visited: {r}")
                    if self.stats:
                        self.stats.inc_value("deltafetch/skipped", spider=spider)
                    continue
            elif isinstance(r, (Item, dict)):
                key = self._get_key(response.request)
                self.db[key] = str(time.time())
                if self.stats:
                    self.stats.inc_value("deltafetch/stored", spider=spider)
            yield r

    def _get_key(self, request: Request) -> bytes:
        key = request.meta.get("deltafetch_key") or request_fingerprint(request)
        # request_fingerprint() returns `hashlib.sha1().hexdigest()`, is a string
        return to_bytes(key)
