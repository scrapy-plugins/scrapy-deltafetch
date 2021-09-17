Changes
=======

2.0.0 (2021-09-20)
------------------
* drop Python 2 support
* replace bsddb3 with Python's dbm for storing request data
* [dev workflow] changed from Travis to Github Actions

1.2.1 (2017-02-09)
------------------

* Use python idiom to check key in dict
* Update minimum Scrapy version supported by this extension to v1.1.0

1.2.0 (2016-12-07)
------------------

* Log through ``logging`` module instead of (deprecated) scrapy's spider.log().
* Fix README on passing ``deltafetch_reset`` argument on the command line.


1.1.0 (2016-06-29)
------------------

Adds support for callbacks returning dict items.


1.0.1 (2016-06-27)
------------------

Fix package URL in setup.py


1.0.0 (2016-06-27)
------------------

Initial release.

This version is functionally equivalent to scrapylib's v1.7.0
``scrapylib.deltafetch.DeltaFetch``.

The only (and major) difference is that support for ``bsddb`` is dropped
in favor of ``bsddb3``, which is a new required dependency.

.. note::
    `bsddb`_ has been deprecated since Python 2.6,
    and even removed in Python 3


.. _bsddb: https://docs.python.org/2/library/bsddb.html
