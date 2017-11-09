#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
import datetime
import os
import sys
import time
import unicodedata
import dropbox
import time
import shutil
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from argparse import ArgumentParser
from utils.dropbox_content_hasher import DropboxContentHasher

def read_access_token(token_file='.dbsync_access_token_file'):
    """ Extracts the access token from an external file 

    Returns the extracted access token
    """
    try:
        f = open(os.path.join(os.path.expanduser('~'),token_file))
        token = f.readlines()[0]
        return token
    except:
        print("Error retrieving token...exiting...")
        return False
        sys.exit()

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

def compute_dbdir_index(dbx, db_folder):
    # print(db_folder)
    content = dbx.files_list_folder(db_folder, recursive = True)

    files = []
    subdirs = []
    index = {}
    content_hash = {}
    for entry in content.entries:
        # print(entry)
        if type(entry) == dropbox.files.FileMetadata:
            file_name = entry.path_display[len(db_folder) + 1:]
            files.append(file_name)
            index[file_name] = entry.server_modified
            content_hash[file_name] = entry.content_hash
        elif type(entry) == dropbox.files.FolderMetadata:
            folder_name = entry.path_display[len(db_folder) + 1:]
            
            if folder_name != '':
                # print(folder_name)
                subdirs.append(folder_name)
    return dict(files=files, subdirs=subdirs, index=index, content_hash=content_hash)

def compute_content_hash(file_path):
    hasher = DropboxContentHasher()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(1024)  # or whatever chunk size you want
            if len(chunk) == 0:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

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
    # print("Dropbox changes called")
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
                        upload_file(dbx, file_path, e.path_display)
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
    '''Downloads a file from dropbox into a buffer and returns the buffer.'''
    try:
        md, res = dbx.files_download(path)
    except dropbox.exceptions.HttpError as err:
        print('*** HTTP error', err)
        return None
    data = res.content
    # print(len(data), 'bytes; md:', md)
    return data

def upload_file(dbx, file_path, path):
    """ 
    file_path is the file to upload
    path is the path on dropbox to upload to
    """
    f = open(file_path)
    file_size = os.path.getsize(file_path)

    CHUNK_SIZE = 4 * 1024 * 1024

    if file_size <= CHUNK_SIZE:
        try:
            print(dbx.files_upload(f.read(), path, mode=dropbox.files.WriteMode.overwrite))
        except:
            print("Error uploading file: ", file_path)

    else:
        try:
            upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
            cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id,
                                                       offset=f.tell())
            commit = dropbox.files.CommitInfo(path=path, mode=dropbox.files.WriteMode.overwrite)

            while f.tell() < file_size:
                if ((file_size - f.tell()) <= CHUNK_SIZE):
                    print(dbx.files_upload_session_finish(f.read(CHUNK_SIZE),
                                                    cursor,
                                                    commit))
                else:
                    dbx.files_upload_session_append(f.read(CHUNK_SIZE),
                                                    cursor.session_id,
                                                    cursor.offset)
                    cursor.offset = f.tell()
        except:
            print("Error uploading file: ", file_path)

def client_changes(dbx, diff1, diff2, folder, db_folder):
    print("client changes")
    # just the newly added files
    diffs = compute_diff(diff1, diff2)
    print("diffs: ", diffs)
    changes = False
    
    for f in diffs['created']:
        file_name = f
        file_path = os.path.join(folder, str(file_name))
        dp_path = db_folder + "/" + str(file_name)
        print("path dbx: ", dp_path)
        print("push uploading to new thread...")
        t = threading.Thread(target=upload_file, name="uploading_thread", args=(dbx, file_path, dp_path))
        #upload_file(dbx, file_path, db_folder + "/" + f)
        t.daemon = True
        t.start()


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

        print("push uploading to new thread...")
        t = threading.Thread(target=upload_file, name="uploading_thread", args=(dbx, file_path, db_folder + "/" + f))
        #upload_file(dbx, file_path, db_folder + "/" + f)
        t.daemon = True
        t.start()
        
        changes = True
    return changes

def check_folder_exists(dbx, db_folder):
    try:
        dbx.files_list_folder_get_latest_cursor(db_folder)
        return True
    except dropbox.exceptions.ApiError as e:
        # print(e)
        if e.error == 'not_found':
            return False

def upload_folder(dbx, folder,db_folder):
    for dir_name, dirs, files in os.walk(folder):
        for file_name in files:
            try: 
                new_dir = dir_name[len(folder):]
                #Create a new folder in the dropbox folder
                new_folder = db_folder + new_dir
                try:
                    metadata =  dbx.files_get_metadata(new_folder)
                except dropbox.exceptions.ApiError as e:
                    dbx.files_create_folder(path=new_folder)
                    
                file_path = os.path.join(dir_name, file_name)
                dest_path = os.path.join(new_folder, file_name)  
                #with open(file_path, "rb") as f:
                #    dbx.files_upload(f.read(), dest_path, mute=True)
                upload_file(dbx, file_path, dest_path)
            except Exception as e:
                print("Failed to upload %s" % (file_name))
    print("Done.")

def download_folder(dbx, folder, db_folder):
    print("Downloading folder")
    os.makedirs(folder)
    content = dbx.files_list_folder(db_folder, recursive=True)

    for entry in content.entries:
        f_path = folder + "/" + "/".join(str(entry.path_display).split("/")[2:])
        if type(entry) == dropbox.files.FolderMetadata and f_path[:-1] != folder:
            os.makedirs(f_path)
        elif type(entry) == dropbox.files.FileMetadata:
            try:
                res = download_file(dbx, entry.path_display)
            except dropbox.exceptions.ApiError as e:
                print("Cannot download file: ", f, " Error: ", str(e))
            with open(f_path, 'wb') as f:
                f.write(res)
        else:
            pass

def write_file(dbx, file_path, dest_path):
    '''Writes file downloaded from dropbox on the local machine.'''
    file_name = file_path.split("/")[-1]
    try:
        res = download_file(dbx, file_path)
    except dropbox.exceptions.ApiError as e:
        print("Cannot download file: ", file_name, " Error: ", str(e))
    with open(dest_path, 'wb') as f:
        f.write(res)
        f.close();

def initial_check(dbx, folder, db_folder):
    print("Initial check and syncing...")
    log_file = os.path.expanduser("~") + "/." + folder.split("/")[-1] + "_sync"   
    # print(log_file)
    timestamp_exists = False
    try:
        with open(log_file, 'r') as f:
            timestamp = f.read()
        try :
            timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            timestamp_exists = True
        except Exception as e:
            pass
    except IOError:
        with open(log_file, 'w') as f:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # print(current_time)
            f.write(current_time)

    db_folder_exists = check_folder_exists(dbx, db_folder)
    local_folder_exists = os.path.exists(folder)

    #Check if folder exists on dropbox but not on local machine
    if db_folder_exists == True and local_folder_exists == False:
        download_folder(dbx, folder, db_folder)
    #Check if local for exists but not on dropbox
    elif db_folder_exists == None and local_folder_exists == True:
        print("creating folder on Dropbox")
        dbx.files_create_folder(path=db_folder)
        upload_folder(dbx, folder, db_folder)
    #If both exist then merge them
    elif db_folder_exists == True and local_folder_exists == True:
        content = compute_dbdir_index(dbx, db_folder)
        dir_id = compute_dir_index(folder)

        #Download files that exist on dropbox but not locally
        file_diff = list(set(content['files']) - set(dir_id['files']))
        for file_name in file_diff:
            db_time = content['index'][file_name]
            file_path = db_folder + "/" + file_name
            dest_path = folder + "/" + file_name
            # print(db_time)
            if timestamp_exists == False or timestamp <= db_time:
                print("Downloading {}".format(file_name))
                if os.path.exists("/".join(str(dest_path).split("/")[:-1])) == True:
                    write_file(dbx, file_path, dest_path)
                else:
                    print("no folder")
                    os.makedirs("/".join(str(dest_path).split("/")[:-1]))
                    write_file(dbx, file_path, dest_path)
            else:
                print("Deleting from dropbox: ", file_name)
                try:
                    dbx.files_delete(file_path)
                except dropbox.exceptions.ApiError as e:
                    print("Cannot delete file: ", file_name, " Error: ", str(e))

        #Upload files that exist locally but not on dropbox
        file_diff = list(set(dir_id['files']) - set(content['files']))
        for file_name in file_diff:
            # db_time = content['index'][file_name]
            local_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(dir_id['index'][file_name])))
            local_time = datetime.datetime.strptime(local_time, '%Y-%m-%d %H:%M:%S')
            file_path = folder + "/" + file_name
            dest_path = db_folder + "/" + file_name

            # print(local_time)
            if timestamp_exists == False or timestamp <= local_time: 
                print("Uploading {}".format(file_name))
                if check_folder_exists(dbx, "/".join(str(dest_path).split("/")[:-1])) == True:
                    upload_file(dbx, file_path, dest_path)
                else:
                    dbx.files_create_folder(path="/".join(str(dest_path).split("/")[:-1]))
                    upload_file(dbx, file_path, dest_path)
            else:
                print("Deleting from local folder: ", file_name)
                try:
                    os.remove(file_path)
                except Exception as e:
                    print("Cannot delete file: ", file_name, "Error : ", str(e))



        #For files that exist on both, keep the latest copy of the files on both
        file_intersect = list(set(content['files']).intersection(set(dir_id['files'])))
        for file_name in file_intersect:
            db_time = content['index'][file_name]
            local_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(dir_id['index'][file_name])))
            local_time = datetime.datetime.strptime(local_time, '%Y-%m-%d %H:%M:%S')
            f_path = folder + "/" + file_name

            #If the hash matches then the file hasn't changed.
            if compute_content_hash(f_path) == content['content_hash'][file_name]:
                print("{} [content match]".format(file_name))
            else: #Download or upload the file based on the latest timestamp.
                if db_time > local_time:
                    # print("download needed")
                    file_path = db_folder + "/" + file_name
                    dest_path = folder + "/" + file_name
                    print("Downloading {}".format(file_name))
                    write_file(dbx, file_path, dest_path)
                else:
                    # print("upload needed")
                    file_path = folder + "/" + file_name
                    dest_path = db_folder + "/" + file_name
                    print("Uploading {}".format(file_name))
                    upload_file(dbx, file_path, dest_path)

    return log_file

def main():
    parser = ArgumentParser()
    parser.add_argument("-f", "--folder", dest="folder",
            required=True, type=str,  help="takes folder as an argument")

    args, other_args = parser.parse_known_args()

    # create a dropbox client instance
    dbx = dropbox.Dropbox(TOKEN)
    folder = args.folder

    folder = os.path.abspath(folder)
    db_folder = "/" + os.path.abspath(folder).split("/")[-1]

    log_file = initial_check(dbx, folder, db_folder)

    cursor = get_current_cursor(dbx, db_folder)
    dir_id = compute_dir_index(folder)

    time.sleep(1)
    try:
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
            try:
                with open(log_file, 'w') as f:
                    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(current_time)
            except:
                continue
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit()

if __name__=="__main__":
    main()
