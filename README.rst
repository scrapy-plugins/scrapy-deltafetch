=================
scrapy-deltafetch
=================

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

Requirements
============

DeltaFetch middleware depends on Python's bsddb3_ package.

On Ubuntu/Debian, you may need to install ``libdb-dev`` if it's not installed already.

.. _bsddb3: https://pypi.python.org/pypi/bsddb3


Installation
============

Install scrapy-deltafetch using ``pip``::

    $ pip install scrapy-deltafetch


Configuration
=============

1. Add DeltaFetch middleware by including it in ``SPIDER_MIDDLEWARES``
   in your ``settings.py`` file::

      SPIDER_MIDDLEWARES = {
          'scrapy_deltafetch.DeltaFetch': 100,
      }

   Here, priority ``100`` is just an example.
   Set its value depending on other middlewares you may have enabled already.

2. Enable the middleware using ``DELTAFETCH_ENABLED`` in your ``setting.py``::

      DELTAFETCH_ENABLED = True


Usage
=====

Following are the different options to control DeltaFetch middleware
behavior.

Supported Scrapy settings
-------------------------

* ``DELTAFETCH_ENABLED`` — to enable (or disable) this extension
* ``DELTAFETCH_DIR`` — directory where to store state
* ``DELTAFETCH_RESET`` — reset the state, clearing out all seen requests

These usually go in your Scrapy project's ``settings.py``.


Supported Scrapy spider arguments
---------------------------------

* ``deltafetch_reset`` — same effect as DELTAFETCH_RESET setting

Example::

    $ scrapy crawl example -a deltafetch_reset=1


Supported Scrapy request meta keys
----------------------------------

* ``deltafetch_key`` — used to define the lookup key for that request. by
  default it's Scrapy's default Request fingerprint function,
  but it can be changed to contain an item id, for example.
  This requires support from the spider, but makes the extension
  more efficient for sites that many URLs for the same item.


