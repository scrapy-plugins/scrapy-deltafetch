Changes
=======


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
