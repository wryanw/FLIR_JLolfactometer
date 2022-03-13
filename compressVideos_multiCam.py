#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 10:26:20 2019

@author: W. Ryan Williamson
"""
import subprocess
from multiprocessing import Process
import glob
import os
from pathlib import PurePath
import cv2
import sys, linecache
import multiCam_utils as multiCam
import pickle

class multiCam_compress(Process):
    def __init__(self):
        super().__init__()
        
    def run(self):
        try:
            dirlist = list()
            destlist = list()
            user_cfg = multiCam.read_config()
            read_dir = user_cfg['compressed_video_dir']
            write_dir = user_cfg['compressed_video_dir']
            prev_date_list = [name for name in os.listdir(read_dir)]
            for f in prev_date_list:
                unit_dirR = os.path.join(read_dir, f, user_cfg['unitRef'])
                unit_dirW = os.path.join(write_dir, f, user_cfg['unitRef'])
                if os.path.exists(unit_dirR):
                    prev_expt_list = [name for name in os.listdir(unit_dirR)]
                    for s in prev_expt_list:
                        dirlist.append(os.path.join(unit_dirR, s))
                        destlist.append(os.path.join(unit_dirW, s))
                            
            
            for ndx, s in enumerate(dirlist):
                avi_list = os.path.join(s, '*.avi')
                vid_list = glob.glob(avi_list)
                if not os.path.exists(destlist[ndx]):
                    os.makedirs(destlist[ndx])
                if len(vid_list):
                    proc = list()
                    for v in vid_list:
                        vid_name = PurePath(v)
                        dest_path = os.path.join(destlist[ndx], vid_name.stem+'.mp4')
                        command = '/usr/bin/ffmpeg -y -i ' + v + ' -c:v libx265 -preset veryfast -strict experimental -crf 17 -loglevel quiet ' + str(dest_path)
                        proc.append(subprocess.Popen(command, shell=True, stdout=subprocess.PIPE))
                    for p in proc:
                        p.wait()
                    passvals = list()
                    for v in vid_list:
                        vid_name = PurePath(v)
                        dest_path = os.path.join(destlist[ndx], vid_name.stem+'.mp4')
                        passval = self.testVids(v,str(dest_path))
                        passvals.append(passval)
                        if passval:
                            os.remove(v)
                            print('Deleted original video')
                        else:
                            print('Error while compressing')
        except:
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
            print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
            
    def testVids(self, v, dest_path):
        try:
            vid = cv2.VideoCapture(v)
            numberFramesA = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
            vid = cv2.VideoCapture(str(dest_path))
            numberFramesB = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
            if numberFramesA == numberFramesB and numberFramesB > 0:
                passval = True
            else:
                passval = False
        except:
            passval = False
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
            print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
            
        return passval
