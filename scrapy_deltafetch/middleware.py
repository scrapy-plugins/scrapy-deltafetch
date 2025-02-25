import dbm
import logging
import time
from pathlib import Path

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.http import Request
from scrapy.item import Item
from scrapy.utils.project import data_path
from scrapy.utils.python import to_bytes
from scrapy.utils.request import request_fingerprint

logger = logging.getLogger(__name__)


class DeltaFetch:
    """Spider middleware to ignore requests to pages containing items seen in
    previous crawls of the same spider, thus producing a "delta crawl"
    containing only new items.

    This also speeds up the crawl, by reducing the number of requests that need
    to be crawled, and processed (typically, item requests are the most cpu
    intensive).
    """

    def __init__(self, dir, reset=False, stats=None):
        self.dir = dir
        self.reset = reset
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):  # noqa: D102
        s = crawler.settings
        if not s.getbool("DELTAFETCH_ENABLED"):
            raise NotConfigured
        dir = data_path(s.get("DELTAFETCH_DIR", "deltafetch"))
        reset = s.getbool("DELTAFETCH_RESET")
        o = cls(dir, reset, crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):  # noqa: D102
        dir = Path(self.dir)
        dir.mkdir(parents=True, exist_ok=True)
        # TODO may be tricky, as there may be different paths on systems
        dbpath = dir / f"{spider.name}.db"
        reset = self.reset or getattr(spider, "deltafetch_reset", False)
        flag = "n" if reset else "c"
        try:
            self.db = dbm.open(dbpath, flag=flag)  # noqa: SIM115
        except Exception:
            logger.warning(
                f"Failed to open DeltaFetch database at {dbpath}, trying to recreate it"
            )
            if dbpath.exists():
                dbpath.unlink()
            self.db = dbm.open(dbpath, "c")  # noqa: SIM115

    def spider_closed(self, spider):  # noqa: D102
        self.db.close()

    def process_spider_output(self, response, result, spider):  # noqa: D102
        for r in result:
            if isinstance(r, Request):
                key = self._get_key(r)
                if key in self.db and self._is_enabled_for_request(r):
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

    def _get_key(self, request):
        key = request.meta.get("deltafetch_key") or request_fingerprint(request)
        return to_bytes(key)

    def _is_enabled_for_request(self, request):
        # Gives you option to disable deltafetch for some requests
        return request.meta.get("deltafetch_enabled", True)
