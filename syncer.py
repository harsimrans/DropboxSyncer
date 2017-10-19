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
import shutil

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

def dropbox_changes(dbx, old_cursor, folder, db_folder):
    print("Dropbox changes called")
    changes = dbx.files_list_folder_continue(old_cursor)
    print("Changes: ", changes.entries)

    any_changes = False

    if len(changes.entries) > 0:
        any_changes = True
        for e in changes.entries:

            file_path = folder + "/" + "/".join(str(e.path_display).split("/")[2:])  #########
            print ("Filepath: ", file_path) 
            print("Processing file: ", e.path_display)
            if type(e) == dropbox.files.DeletedMetadata:
                
                # check if a directory
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            elif type(e) == dropbox.files.FileMetadata:
                if os.path.isfile(file_path):
                    # compare the time stamps
                    #print ("mtime: ", os.stat(file_path).st_mtime)
                    t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(os.path.getmtime(file_path))))
                    #print("time time :", t)
                    t = datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
                    if t <= e.server_modified:
                        print(file_path, 'exists with different stats, downloading')
                        try:
                            res = download_file(dbx, e.path_display)
                        except dropbox.exceptions.ApiError as e:
                            print("Cannot download file: ", f, " Error: ", str(e))

                        with open(file_path) as f:
                            data = f.read()
                        if res == data:
                           print(file_path, 'is already synced [content match]')
                        else: # write this file
                            f=open(file_path,'w')
                            f.write(res)
                            f.close();
                    else:
                        with open(file_path, "rb") as f:
                            try:
                                dbx.files_upload(f.read(), e.path_display, mute=True)
                            except dropbox.exceptions.ApiError as e:
                                print("Cannot upload file: ", f, " Error: ", str(e))
                else:
                    # download the file
                    try:
                        res = download_file(dbx, e.path_display)
                    except dropbox.exceptions.ApiError as e:
                        print("Cannot download file: ", f, " Error: ", str(e))

                    if not os.path.exists(os.path.dirname(file_path)):
                        try:
                            os.makedirs(os.path.dirname(file_path))
                        except OSError as exc: # Guard against race condition
                            if exc.errno != errno.EEXIST:
                                raise
                    f=open(file_path,'w')
                    f.write(res)
                    f.close()
            elif type(e) == dropbox.files.FolderMetadata:
                if not os.path.exists(file_path): ## potential race condition
                    os.makedirs(file_path)
            else:
                print("Could upload or download (error with API ?)")

    # return the latest cursor
    return get_current_cursor(dbx, db_folder), any_changes

def get_current_cursor(dbx, db_folder):
    a = dbx.files_list_folder_get_latest_cursor(db_folder, recursive=True)
    return a.cursor

def exists(dbx, path):
    try:
        dbx.files_get_metadata(path)
        return True
    except:
        return False

def download_file(dbx, path):
    try:
        md, res = dbx.files_download(path)
    except dropbox.exceptions.HttpError as err:
        print('*** HTTP error', err)
        return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data

def client_changes(dbx, diff1, diff2, folder, db_folder):
    print("client changes")
    # just the newly added files
    diffs = compute_diff(diff1, diff2)
    print("diffs: ", diffs)
    changes = False
    
    for f in diffs['created']:
        file_name = f
        file_path = os.path.join(folder, str(file_name))
        with open(file_path, 'rb') as file:
            dp_path = db_folder + "/" + str(file_name)
            print("path dbx: ", dp_path)
            try:
                dbx.files_upload(file.read(), dp_path , mute=True)
            except dropbox.exceptions.ApiError as e:
                print("Cannot upload file: ", f, " Error: ", str(e))
        changes = True

    for f in diffs['deleted']:
        print("deleted: ", f)
        try:
            dbx.files_delete(db_folder + "/" + str(f))
        except dropbox.exceptions.ApiError as e:
            print("Cannot delete file: ", f, " Error: ", str(e))
        changes = True

    for f in diffs['deleted_dirs']:
        print("deleted: ", f)
        try:
            dbx.files_delete(db_folder + "/" + str(f))
        except dropbox.exceptions.ApiError as e:
            print("Cannot delete file: ", f, " Error: ", str(e))
        changes = True

    for f in diffs['updated']:
        print("updated: ", f) 
        file_path = folder + "/" + f
        with open(file_path, "rb") as fname:
            # check if file present on Dropbox
            try:
                if exists(dbx, db_folder + "/" + f):
                    dbx.files_upload(fname.read(), db_folder + "/" + f, mode=dropbox.files.WriteMode.overwrite, mute=True)
                else:
                    dbx.files_upload(fname.read(), db_folder + "/" + f, mute=True)
            except dropbox.exceptions.ApiError as e:
                print("Cannot upload file: ", f, " Error: ", str(e))

        changes = True
    return changes

def check_folder_exists(dbx, db_folder):
    try:
        dbx.files_list_folder_get_latest_cursor(db_folder)
        return True
    except dropbox.exceptions.ApiError as e:
        print(e)
        if e.error == 'not_found':
            return False




def main():
    # create a dropbox client instance
    dbx = dropbox.Dropbox(TOKEN)
    folder = sys.argv[1].strip("/")
    print(os.path.abspath(folder))
    folder = os.path.abspath(folder)
    db_folder = "/" + os.path.abspath(folder).split("/")[-1]
    print("dropbox folder", db_folder)
    # check for Dropbox folder
    print("Checking the folder:::::: ", check_folder_exists(dbx, db_folder))
    try:
        print("metadata: ", dbx.files_get_metadata(db_folder))
    except dropbox.exceptions.ApiError as e:
        print("creating folder on Dropbox")
        dbx.files_create_folder(path=db_folder)

    cursor = get_current_cursor(dbx, db_folder)
    dir_id = compute_dir_index(folder)
    time.sleep(1)
    while True:
        cursor, changes = dropbox_changes(dbx, cursor, folder, db_folder)
        if changes:
            # we made changes to the client, get new index
            dir_id = compute_dir_index(folder)
        time.sleep(1)
        curr_dir_id = compute_dir_index(folder)
        
        # scan for changes
        if client_changes(dbx, curr_dir_id, dir_id, folder, db_folder):
            # we have updates dropbox get new snapshot
            cursor = get_current_cursor(dbx, db_folder)
        dir_id = curr_dir_id
        time.sleep(1)

### TODO: store the cursor and exit and use that initially as old cursor
if __name__=="__main__":
    main()
