[![Build Status](https://travis-ci.org/harsimrans/DropboxSyncer.svg?branch=master)](https://github.com/harsimrans/DropboxSyncer)

# DropboxSyncer: RealTime Sync for Dropbox folders
This tools syncs the folder specified by the user on the personal machine with Dropbox. This sync happens automatically in realtime without any user input. Simply launch the script and get to work, DropboxSyncer will take care of the rest.

```python
usage: dsync [-h] -f FOLDER
example: dsync -f ~/myfolder
```

# Install
you can install it via pip
```
pip install dropbox-sync
```
or clone the repository and run /dropbox_sync/syncer.py

# What's different:
Other tools which are out there only download and upload when user explicitly runs the command. Moreover since there are a lot of conflict due to untimely syncing i.e sync only when users requests not as and when they occur. Therefore, every single time user runs the command, his/her input is needed to resolve the conflicts them. 

DropboxSyncer constly keeps track of any changes and keeps then in sync with the cloud storage. Even on first start, the sync processed is optimized to run quickly and get going ASAP. All you need to do it run DropboxSyncer and forget about it. 

# Getting the Dropbox Access Token
1) Head to https://www.dropbox.com/developers/apps/create 
2) Select Dropbox API
3) Pick an option either Full Dropbox access or App folder*
4) Give your app the name
5) Using OAuth generate your token. Keep this token with you.
6) Create the following file (.dbsync_access_token_file) in your HOME folder and copy the token to this file. The path is ~/.dbsync_access_token_file. Remember not to introduce any extra chacters or spaces during copy.
7) Go to the Usage instruction at the top !!

*At this time it is suggested to use APP folder options. The DropboxSyncer is still evolving. Though you can try the full access option but remember the disclaimer.


# Motivation:
Many times I have run scripts on my personal machine but the computation power on my personal machine is limited. So I usually run the scripts on HPCs. After seeing the results you end up with chain of tweaks to the initial script. The script versions are different now on your personal machine and the cluster. So when you get to your personal machine you no longer have the latest copy. This tool solves this very problem.

### Contributions
Want to add features, fix existing bugs, find new bugs....contributions of all kind are welcomed. 

<b>*DISCLAIMER:*</b></br> I take no responsibility for any fault or damage caused by any procedures of the app. No warranties of any kind are given.

