from setuptools import setup

VERSION = '0.1-alpha'
DOWNLOAD_URL = ('https://github.com/harsimrans/DropboxSyncer/archive/'
                '{}.zip'.format(VERSION))
REQUIRES = ['dropbox']

setup(
    name='dropbox-sync',
    version=VERSION,
    license='MIT',
    scripts=['dropbox-sync/syncer.py'],
    author='harsimran singh',
    author_email='harsimransingh032@gmail.com',
    download_url=DOWNLOAD_URL,
    install_requires=REQUIRES,
    packages=['dropbox-sync'],
    include_package_data=True,
    zip_safe=False,
    url='https://github.com/harsimrans/DropboxSyncer',
    description='Syncs dropbox folder mentioned realtime',
)