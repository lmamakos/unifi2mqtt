# coding=utf-8
import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="huunifie",
    version="0.4.1",
    author="KurisuD",
    author_email="KurisuD@pypi.darnand.net",
    description="""A Hue bridge and Unifi controller client.
 Enables/disables specified Hue schedules in the presence/absence of specified wifi devices on the Unifi controller.""",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KurisuD/huunifie",
    packages=setuptools.find_packages(),
    install_requires=['pathlib', 'requests', 'pap_logger', 'argparse'],
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "License :: Public Domain",
        "Operating System :: OS Independent",
        "Topic :: Home Automation"
    ],
)
