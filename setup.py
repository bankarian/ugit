#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name="ugit",
      version="1.0",
      packages=['ugit'],
      author='Benny Chen',
      entry_points={'console_scripts': ['ugit = ugit.cli:main']})
