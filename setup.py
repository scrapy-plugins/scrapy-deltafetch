from setuptools import find_packages, setup

with open(
    "README.rst",
) as fh:
    long_description = fh.read()

setup(
    name="scrapy-deltafetch",
    version="1.2.1",
    description="Scrapy middleware to ignore previously crawled pages",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Scrapinghub",
    author_email="info@scrapinghub.com",
    maintainer="Rabin Adhikari",
    maintainer_email="rabin.adk1@gmail.com",
    url="http://github.com/scrapy-plugins/scrapy-deltafetch",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    license="BSD",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=["Scrapy>=2.3.0", "bsddb3"],
    python_requires=">=3.6",
    zip_safe=True,
)
