# -*- coding: utf-8 -*-
# -*- mode: python -*-
import os
import sys
from setuptools import setup, find_packages
if sys.hexversion < 0x03050000:
    raise RuntimeError("Python 3.5 or higher required")


VERSION = '0.7.5'
cls_txt = """
Development Status :: 4 - Beta
Framework :: Django
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Internet :: WWW/HTTP
Topic :: Internet :: WWW/HTTP :: Dynamic Content
"""

setup(
    name="django-bird-colony",
    version=VERSION,
    description="A simple Django app for managing a bird breeding colony",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    long_description_content_type="text/markdown",
    classifiers=[x for x in cls_txt.split("\n") if x],
    author='C Daniel Meliza',
    maintainer='C Daniel Meliza',
    url="https://github.com/melizalab/django-bird-colony",
    packages=find_packages(exclude=["*test*"]),
    include_package_data=True,
)
