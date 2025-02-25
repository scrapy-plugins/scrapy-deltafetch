from pathlib import Path

from setuptools import setup

setup(
    name="scrapy-deltafetch",
    version="2.0.1",
    license="BSD",
    description="Scrapy middleware to ignore previously crawled pages",
    long_description=Path("README.rst").read_text(encoding="utf-8"),
    author="Zyte",
    author_email="opensource@zyte.com",
    url="http://github.com/scrapy-plugins/scrapy-deltafetch",
    packages=["scrapy_deltafetch"],
    platforms=["Any"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    install_requires=["Scrapy>=1.1.0"],
    python_requires=">=3.9",
)
