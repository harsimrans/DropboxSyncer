from __future__ import print_function
from dropbox_sync import syncer
import pytest
import pyfakefs.fake_filesystem as fake_fs
import os

def test_read_access_token():
	assert(syncer.read_access_token('some_non_existant_file_path')) == False
	assert(syncer.read_access_token()) != None

def test_compute_dir_index(fs):
	files = ["/abc/def.txt", "/abc/efg.png", "/abc/hgf.pdf", "/something.txt"]
	directories = ["abc/har", "bcd", "/def"]
	## /var folder happens to be appearing on Mac OS with pyfake
	## HACK: check if present remove it. FIGURE OUT WHY !! FIX IT !!!!
	if os.path.exists("/var"):
		fs.RemoveObject("/var")

	# for root, dirs, filenames in os.walk("/"):
	# 	print(root, dirs, filenames) 
	for entry in directories:
		fs.CreateDirectory(entry)
	for entry in files:
		fs.CreateFile(entry)
	
	for root, dirs, filenames in os.walk("/"):
		print(root, dirs, filenames) 
	
	d = syncer.compute_dir_index("/")	
	
	print(d['files'], d['subdirs'])
	assert(len(d['files']) == 4)
	assert(len(d['subdirs']) == 4)

def test_compute_diff(fs):
	files = ["/abc/def.txt", "/abc/efg.png", "/abc/hgf.pdf", "/something.txt"]
	directories = ["abc/har", "bcd", "/def"]
	for entry in directories:
		fs.CreateDirectory(entry)
	for entry in files:
		fs.CreateFile(entry)
	
	diff1 = syncer.compute_dir_index("/")

	fs.RemoveObject("/something.txt")
	fs.RemoveObject("/abc/def.txt")
	fs.CreateFile("/abc/def.txt",
		contents="Dear Prudence\\nWon\\'t you come out to play?\\n")
	fs.RemoveObject("/def")
	fs.CreateFile("/something2.txt",
		contents="Dear Prudence\\nWon\\'t you come out to play?\\n")

	diff2 = syncer.compute_dir_index("/")
	
	diffs = syncer.compute_diff(diff2, diff1)
	assert(len(diffs['deleted']) == 1)
	assert(len(diffs['updated']) == 1)
	assert(len(diffs['deleted_dirs']) == 1)
	assert(len(diffs['created']) == 1)
