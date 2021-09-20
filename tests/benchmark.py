import tempfile

import mock
from scrapy import Request, Spider
from scrapy.statscollectors import StatsCollector
from scrapy.utils.test import get_crawler

from scrapy_deltafetch import DeltaFetch


def benchmark_middleware(result):
    spider_name = 'df_tests'
    spider = Spider(spider_name)
    temp_dir = tempfile.gettempdir()
    crawler = get_crawler(Spider)
    stats = StatsCollector(crawler)
    mw = DeltaFetch(temp_dir, reset=False, stats=stats)
    mw.spider_opened(spider)
    response = mock.Mock()
    response.request = Request('http://url',
                               meta={'deltafetch_key': 'key'})

    for x in mw.process_spider_output(response, result, spider):
        pass

def test_middleware(benchmark):
    result = []
    for x in range(50000):
        request = Request(f'https://{x}')
        result.append(request)
    result = benchmark(benchmark_middleware, result)
