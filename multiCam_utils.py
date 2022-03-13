#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 10:26:20 2019

@author: W. Ryan Williamson
"""

from pathlib import Path
import os.path
import yaml
import ruamel.yaml
import glob
import os
from pathlib import PurePath
import cv2
import sys, linecache
import shutil
from multiprocessing import Process

class moveVids(Process):
    def __init__(self):
        super().__init__()
        
    def run(self):
        try:
            dirlist = list()
            destlist = list()
            user_cfg = read_config()
            read_dir = user_cfg['raw_data_dir']
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
                    for v in vid_list:
                        vid_name = PurePath(v)
                        dest_path = os.path.join(destlist[ndx], vid_name.stem+'.avi')
                        shutil.copyfile(v,dest_path)
                            
                    passvals = list()
                    for v in vid_list:
                        vid_name = PurePath(v)
                        dest_path = os.path.join(destlist[ndx], vid_name.stem+'.avi')
                        passval = self.testVids(v,str(dest_path))
                        passvals.append(passval)
                        if passval:
                            # print(v)
                            os.remove(v)
                            print('Deleted original video')
                        else:
                            print('Error while moving')
                metafiles = glob.glob(os.path.join(s,'*'))
                for m in metafiles:
                    mname = PurePath(m).name
                    mdest = os.path.join(destlist[ndx],mname)
                    if not os.path.isfile(mdest):
                        shutil.copyfile(m,mdest)
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

def read_config():
    """
    Reads structured config file

    """
    usrdatadir = os.path.dirname(os.path.realpath(__file__))
    configname = os.path.join(usrdatadir, 'userdata.yaml')
    ruamelFile = ruamel.yaml.YAML()
    path = Path(configname)
    cfg = ''
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                cfg = ruamelFile.load(f)
        except Exception as err:
            if err.args[2] == "could not determine a constructor for the tag '!!python/tuple'":
                with open(path, 'r') as ymlfile:
                  cfg = yaml.load(ymlfile,Loader=yaml.SafeLoader)
                  write_config(cfg)
    else:
        print('Config file not found')
    return(cfg)

def write_config(cfg):
    """
    Write structured config file.
    """
    usrdatadir = os.path.dirname(os.path.realpath(__file__))
    configname = os.path.join(usrdatadir, 'userdata.yaml')
    with open(configname, 'w') as cf:
        ruamelFile = ruamel.yaml.YAML()
        ruamelFile.dump(cfg, cf)

def metadata_template():
    """
    Creates a template for config.yaml file. This specific order is preserved while saving as yaml file.
    """
    yaml_str = """\
# Mouse
    ID:
    placeholderA:
    placeholderB:
# Experiment
    Designer:
    StartTime:
    Collection:
    \n
    """
    ruamelFile = ruamel.yaml.YAML()
    cfg_file = ruamelFile.load(yaml_str)
    return cfg_file, ruamelFile

def read_metadata(path):
    ruamelFile = ruamel.yaml.YAML()
    if os.path.exists(path):
        with open(path, 'r') as f:
            cfg = ruamelFile.load(f)
    return(cfg)

def write_metadata(cfg, path):
    with open(path, 'w') as cf:
        ruamelFile = ruamel.yaml.YAML()
        ruamelFile.dump(cfg, cf)
