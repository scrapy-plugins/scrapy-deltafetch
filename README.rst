scrapy-deltafetch
-----------------

.. image:: https://travis-ci.org/scrapy-plugins/scrapy-deltafetch.svg?branch=master
    :target: https://travis-ci.org/scrapy-plugins/scrapy-deltafetch

.. image:: https://codecov.io/gh/scrapy-plugins/scrapy-deltafetch/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/scrapy-plugins/scrapy-deltafetch

This is a Scrapy spider middleware to ignore requests
to pages containing items seen in previous crawls of the same spider,
thus producing a "delta crawl" containing only new items.

This also speeds up the crawl, by reducing the number of requests that need
to be crawled, and processed (typically, item requests are the most CPU
intensive).

Supported Scrapy settings:

* DELTAFETCH_ENABLED — to enable (or disable) this extension
* DELTAFETCH_DIR — directory where to store state
* DELTAFETCH_RESET — reset the state, clearing out all seen requests

Supported Scrapy spider arguments:

* deltafetch_reset — same effect as DELTAFETCH_RESET setting

Supported Scrapy request meta keys:

* deltafetch_key — used to define the lookup key for that request. by
  default it's the fingerprint, but it can be changed to contain an item
  id, for example. This requires support from the spider, but makes the
  extension more efficient for sites that many URLs for the same item.
