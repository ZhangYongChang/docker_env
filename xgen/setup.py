import os
from setuptools import setup, find_packages

setup(
    name = "xgen",
    version = "0.1.1",
    author = "yczhang",
    author_email = "yczhang@fiberhome.com",
    description = ("Generate xsd/proto/cpp file from yang model."),
    license = "BSD",
    keywords = "xgen",
    url = "http://www.fiberhome.com",
    packages=find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=['pyang==1.7.3', 'jinja2==2.11.3'],
    scripts=['xgenc.py'],
)