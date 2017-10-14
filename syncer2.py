#!/usr/bin/env python
from __future__ import print_function

import argparse
import contextlib
import datetime
import os
import six
import sys
import time
import unicodedata
import dropbox
import time

def read_access_token(token_file='access_token_file'):
    """ Extracts the access token from an external file 

    Returns the extracted access token
    """
    f = open(token_file)
    token = f.readlines()[0]
    return token

# OAuth2 access token.
TOKEN = read_access_token()

def compute_dir_index(path):
    """ Return a tuple containing:
    - list of files (relative to path)
    - lisf of subdirs (relative to path)
    - a dict: filepath => last 
    """
    files = []
    subdirs = []

    for root, dirs, filenames in os.walk(path):
        for subdir in dirs:
            subdirs.append(os.path.relpath(os.path.join(root, subdir), path))

        for f in filenames:
            files.append(os.path.relpath(os.path.join(root, f), path))
        
    index = {}
    for f in files:
        index[f] = os.path.getmtime(os.path.join(path, f))

    return dict(files=files, subdirs=subdirs, index=index)

def compute_diff(dir_base, dir_cmp):
    data = {}
    data['deleted'] = list(set(dir_cmp['files']) - set(dir_base['files']))
    data['created'] = list(set(dir_base['files']) - set(dir_cmp['files']))
    data['updated'] = []
    data['deleted_dirs'] = list(set(dir_cmp['subdirs']) - set(dir_base['subdirs']))

    for f in set(dir_cmp['files']).intersection(set(dir_base['files'])):
        if dir_base['index'][f] != dir_cmp['index'][f]:
            data['updated'].append(f)
    return data

def dropbox_changes(dbx, old_cursor):
    print("Dropbox changes called")
    changes = dbx.files_list_folder_continue(old_cursor)
    print("Changes: ", changes.entries)
    if len(changes.entries) > 0:
        for e in changes.entries:
            file_path = str(".") + str(e.path_display) #########
            print ("Filepath: ", file_path) 
            print("Processing file: ", e.path_display)
            if type(e) == dropbox.files.DeletedMetadata:
                os.remove(file_path)
            elif type(e) == dropbox.files.FileMetadata:
                if os.path.isfile(file_path):
                    # compare the time stamps
                    print ("mtime: ", os.stat(file_path).st_mtime)
                    t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(os.path.getmtime(file_path))))
                    print("time time :", t)
                    t = datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
                    if t <= e.server_modified:
                        print(file_path, 'exists with different stats, downloading')
                        res = download_file(dbx, e.path_display)
                        with open(file_path) as f:
                            data = f.read()
                        if res == data:
                           print(name, 'is already synced [content match]')
                        else: # write this file
                            f=open(file_path,'w')
                            f.write(res)
                            f.close();
                    else:
                        with open(file_path, "rb") as f:
                            dbx.files_upload(f.read(), e.path_display, mute=True)
                else:
                    # download the file
                    res = download_file(dbx, e.path_display)
                    f=open(file_path,'w')
                    f.write(res)
                    f.close();
            else:
                print("Could upload or download (error with API ?")

    # return the latest cursor
    return get_current_cursor(dbx)

def get_current_cursor(dbx):
    a = dbx.files_list_folder_get_latest_cursor("/testfolder") ##########
    return a.cursor

def download_file(dbx, path):
    try:
        md, res = dbx.files_download(path)
    except dropbox.exceptions.HttpError as err:
        print('*** HTTP error', err)
        return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data

def main():
    # create a dropbox client instance
    dbx = dropbox.Dropbox(TOKEN)

    cursor = get_current_cursor(dbx)
    time.sleep(5)
    while True:
        cursor = dropbox_changes(dbx, cursor)
        time.sleep(10)

'''
def main():
    
    # check if anything updated on Dropbox

    # always be your root folder on Dropbox
    folder = "./testfolder"

    # get the current snapshot
    snap_old = compute_dir_index(folder)
    while True:
        time.sleep(10)
        snap_new = compute_dir_index(folder)
        diff = compute_diff(snap_new, snap_old)
        print("diff: ", diff)
        changes = False
        for key in diff:
            if len(diff[key]) != 0:
                changes = True
                snap_old = snap_new
                break
        if changes:
            # do a task
            print("detected a change")
            # reflect these changes on dropbox

            #delete from dropbox
            # push to dropbox

'''
if __name__=="__main__":
    main()