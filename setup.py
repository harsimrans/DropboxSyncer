from setuptools import setup, find_packages

VERSION = '0.1-alpha'
DOWNLOAD_URL = ('https://github.com/harsimrans/DropboxSyncer/archive/'
                '{}.zip'.format(VERSION))
REQUIRES = ['dropbox']

PACKAGES = find_packages(exclude=["*.tests", "*.tests.*", "tests.*",
                                    "tests"])

add_keywords = dict(
    entry_points={
        'console_scripts': ['dsync=dropbox_sync.syncer:main'],
    }, )

setup(
    name='dropbox-sync',
    version=VERSION,
    license='MIT',
    author='harsimran singh',
    author_email='harsimransingh032@gmail.com',
    download_url=DOWNLOAD_URL,
    install_requires=REQUIRES,
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=False,
    url='https://github.com/harsimrans/DropboxSyncer',
    description='Syncs dropbox folder mentioned realtime',
     **add_keywords
)
