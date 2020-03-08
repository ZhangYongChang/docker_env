import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now
# 1) we have a top level README file and
# 2) it's easier to type in the README file than to put a raw
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

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
    install_requires=['pyang==1.7.3'],
    scripts=['bundle.py'],
)