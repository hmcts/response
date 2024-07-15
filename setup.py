import os
from os import path

from setuptools import find_packages, setup

VERSION = "0.0.1"

INSTALL_REQUIRES = [
    "Django>=2.2.9,<4",
    "bleach==4.0.0",
    "bleach-whitelist>=0.0.11",
    "cryptography>=42.0.8",
    "django-after-response>=0.2.2",
    "django-bootstrap4>=22.1",
    "djangorestframework>=3.13.1",
    "emoji-data-python==1.5.0",
    "jsonfield>=3.1.0",
    "markdown2>=2.4.13",
    "python-slugify>=8.0.4",
    "slackclient>=1.3,<2",
]

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# load README.md
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="response",
    version=VERSION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude="demo"),
    install_requires=INSTALL_REQUIRES,
    package_dir={"response": "response"},
    python_requires=">3.6",
    include_package_data=True,
    license="MIT License",  # example license
    description="A real-time incident response and reporting tool",
    url="https://github.com/hmcts/response",
    author="Enda Kelly",
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
