[![Build Status](https://travis-ci.org/harsimrans/DropboxSyncer.svg?branch=master)](https://github.com/harsimrans/DropboxSyncer)

# DropboxSyncer: RealTime Sync for Dropbox folders
This tools syncs the folder specified by the user on the personal machine with Dropbox. This sync happens automatically in realtime without any user input. Simply launch the script and get to work, DropboxSyncer will take care of the rest.

```python
usage: dsync [-h] -f FOLDER
example: dsync -f ~/myfolder
```

### Install
```
pip install dropbox-sync
```

##### Motivation:
Many times I have run scripts on my personal machine but the computation power on my personal machine is limited. So I usually run the scripts on HPCs. After seeing the results you end up with chain of tweaks to the initial script. The script versions are different now on your personal machine and the cluster. So when you get to your personal machine you no longer have the latest copy. This tool solves this very problem.

**What's different:** Other tools which are out there only download and upload when user explicitly runs the command. Moreover since there are a lot of conflict due to untimely syncing, every single time user input is needed to resolve them.

