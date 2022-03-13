"""
multiCam toolbox
https://github.com/wryanw/multiCam
W Williamson, wallace.williamson@ucdenver.edu

"""


from __future__ import print_function
from multiprocessing import Array, Queue, Value
import wx
import wx.lib.dialogs
import os
import numpy as np
import time, datetime
import ctypes
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import multiCam_PySpin_v1 as spin
import multiCam_utils as multiCam
import compressVideos_multiCam as compressVideos
import shutil
from pathlib import Path
# import serial
import ruamel.yaml
import pickle

# ###########################################################################
# Class for GUI MainFrame
# ###########################################################################
class ImagePanel(wx.Panel):

    def __init__(self, parent, gui_size, axesCt, **kwargs):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
            
        self.figure = Figure()
        self.axes = list()
        if axesCt <= 3:
            if gui_size[0] > gui_size[1]:
                rowCt = 1
                colCt = axesCt
            else:
                colCt = 1
                rowCt = axesCt
            
        else:
            if gui_size[0] > gui_size[1]:
                rowCt = 2
                colCt = np.ceil(axesCt/2)
            else:
                colCt = 2
                rowCt = np.ceil(axesCt/2)
        a = 0
        for r in range(int(rowCt)):
            for c in range(int(colCt)):
                self.axes.append(self.figure.add_subplot(rowCt, colCt, a+1, frameon=True))
                self.axes[a].set_position([c*1/colCt+0.005,r*1/rowCt+0.005,1/colCt-0.01,1/rowCt-0.01])
                
        
                self.axes[a].xaxis.set_visible(False)
                self.axes[a].yaxis.set_visible(False)
                a+=1
            
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()

    def getfigure(self):
        """
        Returns the figure, axes and canvas
        """
        return(self.figure,self.axes,self.canvas)

class WidgetPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)

class MainFrame(wx.Frame):
    """Contains the main GUI and button boxes"""
    def __init__(self, parent):
        

# Settting the GUI size and panels design
        displays = (wx.Display(i) for i in range(wx.Display.GetCount())) # Gets the number of displays
        screenSizes = [display.GetGeometry().GetSize() for display in displays] # Gets the size of each display
        index = 0 # For display 1.
        screenW = screenSizes[index][0]
        screenH = screenSizes[index][1]
        
        self.user_cfg = multiCam.read_config()
        key_list = list()
        for cat in self.user_cfg.keys():
            key_list.append(cat)
        self.camStrList = list()
        for key in key_list:
            if 'cam' in key:
                self.camStrList.append(key)
        self.slist = list()
        for s in self.camStrList:
            if not self.user_cfg[s]['ismaster']:
                self.slist.append(str(self.user_cfg[s]['serial']))
            else:
                self.masterID = str(self.user_cfg[s]['serial'])
        
        self.camCt = len(self.camStrList)
        if self.camCt <= 3:
            scaleRefs = [0.6,0.9]
        else:
            scaleRefs = [0.7,0.8]   
        
        self.gui_size = (round(screenW*scaleRefs[0]),round(screenH*scaleRefs[1]))
        if screenW > screenH:
            self.gui_size = (round(screenW*scaleRefs[1]),round(screenH*scaleRefs[0]))
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'multiCam Acquisition - WRW',
                            size = wx.Size(self.gui_size), pos = wx.DefaultPosition, style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("")

        self.SetSizeHints(wx.Size(self.gui_size)) #  This sets the minimum size of the GUI. It can scale now!
        
###################################################################################################################################################
# Spliting the frame into top and bottom panels. Bottom panels contains the widgets. The top panel is for showing images and plotting!
        self.guiDim = 0
        if screenH > screenW:
            self.guiDim = 1
        topSplitter = wx.SplitterWindow(self)
        self.image_panel = ImagePanel(topSplitter,self.gui_size, self.camCt)
        self.widget_panel = WidgetPanel(topSplitter)
        if self.guiDim == 0:
            topSplitter.SplitVertically(self.image_panel, self.widget_panel,sashPosition=self.gui_size[0]*0.75)#0.9
        else:
            topSplitter.SplitHorizontally(self.image_panel, self.widget_panel,sashPosition=self.gui_size[1]*0.75)#0.9
        topSplitter.SetSashGravity(0.5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

###################################################################################################################################################
# Add Buttons to the WidgetPanel and bind them to their respective functions.
        
        

        wSpace = 0
        wSpacer = wx.GridBagSizer(5, 5)
        
        camctrlbox = wx.StaticBox(self.widget_panel, label="Camera Control")
        bsizer = wx.StaticBoxSizer(camctrlbox, wx.HORIZONTAL)
        camsizer = wx.GridBagSizer(5, 5)
        
        bw = 76
        vpos = 0
        self.init = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Enable", size=(bw,-1))
        camsizer.Add(self.init, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.init.Bind(wx.EVT_TOGGLEBUTTON, self.initCams)

        self.reset = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Reset", size=(bw, -1))
        camsizer.Add(self.reset, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.reset.Bind(wx.EVT_BUTTON, self.camReset)
        
        self.update_settings = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Update Settings", size=(bw*2, -1))
        camsizer.Add(self.update_settings, pos=(vpos,6), span=(1,6), flag=wx.ALL, border=wSpace)
        self.update_settings.Bind(wx.EVT_BUTTON, self.updateSettings)
        self.update_settings.Enable(False)

        vpos+=1
        self.play = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Live", size=(bw, -1))
        camsizer.Add(self.play, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.play.Bind(wx.EVT_TOGGLEBUTTON, self.liveFeed)
        self.play.Enable(False)
        
        self.rec = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Record", size=(bw, -1))
        camsizer.Add(self.rec, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.rec.Bind(wx.EVT_TOGGLEBUTTON, self.recordCam)
        self.rec.Enable(False)
        
        self.minRec = wx.TextCtrl(self.widget_panel, value='20', size=(50, -1))
        self.minRec.Enable(False)
        min_text = wx.StaticText(self.widget_panel, label='M:')
        camsizer.Add(self.minRec, pos=(vpos,7), span=(1,2), flag=wx.ALL, border=wSpace)
        camsizer.Add(min_text, pos=(vpos,6), span=(1,1), flag=wx.TOP, border=wSpace)
        
        self.secRec = wx.TextCtrl(self.widget_panel, value='0', size=(50, -1))
        self.secRec.Enable(False)
        sec_text = wx.StaticText(self.widget_panel, label='S:')
        camsizer.Add(self.secRec, pos=(vpos,10), span=(1,2), flag=wx.ALL, border=wSpace)
        camsizer.Add(sec_text, pos=(vpos,9), span=(1,1), flag=wx.TOP, border=wSpace)
        
        # vpos+=1
        # self.set_thresh = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Threshold", size=(101, -1))
        # camsizer.Add(self.set_thresh, pos=(vpos,0), span=(0,4), flag=wx.TOP, border=0)
        # self.set_thresh.Bind(wx.EVT_TOGGLEBUTTON, self.setLines)
        # self.set_thresh.Enable(False)
        
        # self.get_back = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Background", size=(101, -1))
        # camsizer.Add(self.get_back, pos=(vpos,4), span=(0,4), flag=wx.TOP, border=0)
        # self.get_back.Bind(wx.EVT_TOGGLEBUTTON, self.getBack)
        # self.get_back.Enable(False)

        # self.set_drop = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Droplet", size=(101, -1))
        # camsizer.Add(self.set_drop, pos=(vpos,8), span=(0,4), flag=wx.TOP, border=0)
        # self.set_drop.Bind(wx.EVT_TOGGLEBUTTON, self.setLines)
        # self.set_drop.Enable(False)

        camsize = 4
        vpos+=camsize
        bsizer.Add(camsizer, 1, wx.EXPAND | wx.ALL, 5)
        wSpacer.Add(bsizer, pos=(0, 0), span=(camsize,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=wSpace)
        
        
        # serctrlbox = wx.StaticBox(self.widget_panel, label="Serial Control")
        # sbsizer = wx.StaticBoxSizer(serctrlbox, wx.HORIZONTAL)
        # sersizer = wx.GridBagSizer(5, 5)
        # bw = 100
        # vpos = 0
        
        # min_text = wx.StaticText(self.widget_panel, label='Angle:', size=(bw, -1))
        # sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.LEFT, border=wSpace)
        # self.angle_set = wx.SpinCtrl(self.widget_panel, value='0', size=(bw, -1))
        # sersizer.Add(self.angle_set, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        # self.angle_set.SetMax(90)
        # self.angle_set.SetMin(-90)
        # self.angle_set.Bind(wx.EVT_SPINCTRL, self.comFun)

        # self.give_reward = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Dispense", size=(bw, -1))
        # sersizer.Add(self.give_reward, pos=(vpos,6), span=(1,3), flag=wx.LEFT, border=wSpace)
        # self.give_reward.Bind(wx.EVT_BUTTON, self.comFun)
        
        # vpos+=1
        # self.step_sz = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['stepSize']), size=(bw*(9/6), -1))
        # min_text = wx.StaticText(self.widget_panel, label='Reward Step Size:')
        # sersizer.Add(min_text, pos=(vpos,0), span=(1,4), flag=wx.TOP, border=wSpace)
        # sersizer.Add(self.step_sz, pos=(vpos,4), span=(1,4), flag=wx.ALL, border=wSpace)
        # self.step_sz.SetMax(200)
        # self.step_sz.SetValue(str(self.user_cfg['stepSize']))
        # self.step_sz.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        # vpos+=1
        # min_text = wx.StaticText(self.widget_panel, label='Big Step: Rel to Syringe', size=(bw, -1))
        # sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.LEFT, border=wSpace)

        # self.big_in = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Extend", size=(bw, -1))
        # sersizer.Add(self.big_in, pos=(vpos,3), span=(1,3), flag=wx.LEFT, border=wSpace)
        # self.big_in.Bind(wx.EVT_BUTTON, self.comFun)
        
        # self.big_out = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Contract", size=(bw, -1))
        # sersizer.Add(self.big_out, pos=(vpos,6), span=(1,3), flag=wx.LEFT, border=wSpace)
        # self.big_out.Bind(wx.EVT_BUTTON, self.comFun)
        
        # vpos+=1
        # self.set_left = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['leftVal']), size=(65, -1))
        # min_text = wx.StaticText(self.widget_panel, label='Set Left:')
        # sersizer.Add(min_text, pos=(vpos,0), span=(1,2), flag=wx.TOP, border=wSpace)
        # sersizer.Add(self.set_left, pos=(vpos,2), span=(1,2), flag=wx.ALL, border=wSpace)
        # self.set_left.Bind(wx.EVT_SPINCTRL, self.comFun)
        # self.set_left.SetMax(1000)
        # self.set_left.SetValue(str(self.user_cfg['leftVal']))
        
        
        # self.set_right = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['rightVal']), size=(65, -1))
        # min_text = wx.StaticText(self.widget_panel, label='Set Right:')
        # sersizer.Add(min_text, pos=(vpos,5), span=(1,2), flag=wx.TOP, border=wSpace)
        # sersizer.Add(self.set_right, pos=(vpos,7), span=(1,2), flag=wx.ALL, border=wSpace)
        # self.set_right.Bind(wx.EVT_SPINCTRL, self.comFun)
        # self.set_right.SetMax(2600)
        # self.set_right.SetMin(1500)
        # self.set_right.SetValue(str(self.user_cfg['rightVal']))
        
        # vpos+=1
        # puff_text = wx.StaticText(self.widget_panel, label='Puff duration (ms):')
        # sersizer.Add(puff_text, pos=(vpos,0), span=(1,4), flag=wx.LEFT, border=wSpace)
        # self.puff_dur = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['puffDur']), size=(bw, -1))
        # sersizer.Add(self.puff_dur, pos=(vpos,4), span=(1,3), flag=wx.ALL, border=wSpace)
        # self.puff_dur.SetMax(10000)
        # self.puff_dur.SetMin(100)
        # self.puff_dur.SetValue(str(self.user_cfg['puffDur']))
        # self.puff_dur.Bind(wx.EVT_SPINCTRL, self.comFun)

        # self.air_puff = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Puff", size=(bw*0.65, -1))
        # sersizer.Add(self.air_puff, pos=(vpos,7), span=(1,2), flag=wx.LEFT, border=wSpace)
        # self.air_puff.Bind(wx.EVT_BUTTON, self.comFun)
        
        
        # sersize = vpos
        # vpos = camsize
        # sbsizer.Add(sersizer, 1, wx.EXPAND | wx.ALL, 5)
        # wSpacer.Add(sbsizer, pos=(vpos, 0), span=(sersize,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=wSpace)
        # self.serHlist = [self.angle_set, self.give_reward, self.step_sz, self.big_in,
        #                  self.big_out, self.set_right, self.set_left, self.puff_dur, self.air_puff]
        # for h in self.serHlist:
        #     h.Enable(False)

        
        # self.odor_id = wx.TextCtrl(self.widget_panel, id=wx.ID_ANY, value="OdorName")
        # wSpacer.Add(self.odor_id, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        wSpace = 10
        self.expt_id = wx.TextCtrl(self.widget_panel, id=wx.ID_ANY, value="User_defined_session_ref",size=(300, -1))
        wSpacer.Add(self.expt_id, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        vpos+=1
        
        # vpos+=sersize
        self.slider = wx.Slider(self.widget_panel, -1, 0, 0, 100,size=(300, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        wSpacer.Add(self.slider, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.slider.Enable(False)
        
        # usrdatadir = os.path.dirname(os.path.realpath(__file__))
        # self.protoDir = os.path.join(usrdatadir, 'Protocols')
        # protocol_list = [name for name in os.listdir(self.protoDir) if name.endswith('.yaml')]
        # protocol_list = [name[:-5] for name in protocol_list]
        # if not len(protocol_list):
        #     protocol_list = ['None']
        # else:
        #     protocol_list = ['Protocol']+protocol_list
        # self.protocol = wx.Choice(self.widget_panel, size=(100, -1), id=wx.ID_ANY, choices=protocol_list)
        # wSpacer.Add(self.protocol, pos=(vpos,2), span=(0,1), flag=wx.ALL, border=wSpace)
        # self.protocol.SetSelection(0)
        
        self.disable4cam = [self.minRec, self.secRec, self.update_settings,
                            self.expt_id]
                            # , self.set_thresh, self.get_back, self.set_drop]
        self.onWhenCamEnabled = [self.play, self.rec, self.minRec, self.secRec,
                                 self.update_settings]
                                 # , self.set_thresh, self.get_back, self.set_drop]


        # vpos+=1
        
        # self.tone_pair = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Pair Odor with Tone")
        # wSpacer.Add(self.tone_pair, pos=(vpos,0), span=(0,2), flag=wx.LEFT, border=wSpace)
        # self.tone_pair.SetValue(self.user_cfg['tonePair'])
        
        vpos+=3
        
        self.compress_vid = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Compress Videos")
        wSpacer.Add(self.compress_vid, pos=(vpos,0), span=(0,2), flag=wx.LEFT, border=wSpace)
        self.compress_vid.Bind(wx.EVT_BUTTON, self.compressVid)


        self.quit = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Quit")
        wSpacer.Add(self.quit, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.quit.Bind(wx.EVT_BUTTON, self.quitButton)
        self.Bind(wx.EVT_CLOSE, self.quitButton)

        self.widget_panel.SetSizer(wSpacer)
        wSpacer.Fit(self.widget_panel)
        self.widget_panel.Layout()
        
        
        self.liveTimer = wx.Timer(self, wx.ID_ANY)
        self.recTimer = wx.Timer(self, wx.ID_ANY)
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        self.figure.canvas.draw()
        
        self.dropY = int(self.user_cfg['droplet_info']['yVal'])
        self.roi = np.asarray(self.user_cfg['thresh_info']['roiXWYH'], int)
        
        # self.compressThread = compressVideos.multiCam_compress()
        # self.compressThread.start()
        # time.sleep(5)
        # self.mv = multiCam.moveVids()
        # self.mv.start()
            
        self.im = list()
        # self.frmDims = [0,135,0,180]
        self.frmDims = [0,270,0,360]
        self.roi[3] = self.frmDims[1]-self.roi[2]-5
        self.camIDlist = list()
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        self.com = Value(ctypes.c_int, 0)
        self.servoAngle = 0
        self.x = 0
        self.y = 0
        self.dlc_frmct = 3
        self.thresh_h = list()
        self.droplet_h = list()
        self.frame = list()
        self.frameBuff = list()
        self.dtype = 'uint8'
        self.array = list()
        self.frmGrab = list()
        self.size = self.frmDims[1]*self.frmDims[3]
        self.shape = [self.frmDims[1], self.frmDims[3]]
        frame = np.zeros(self.shape, dtype='ubyte')
        self.imBack = np.zeros(self.shape,'ubyte')
        self.maxBack = np.zeros(self.shape,'ubyte')
        self.frmNoBack = np.zeros(self.shape,'ubyte')
        frameBuff = np.zeros(self.size, dtype='ubyte')
        self.dropFindNdcs = np.arange(self.roi[0],self.frmDims[3])
        self.dropSums = np.zeros(len(self.dropFindNdcs))
        for ndx, s in enumerate(self.camStrList):
            self.camIDlist.append(str(self.user_cfg[s]['serial']))
            self.array.append(Array(ctypes.c_ubyte, self.size))
            self.frmGrab.append(Value(ctypes.c_byte, 0))
            self.frame.append(frame)
            self.frameBuff.append(frameBuff)
            self.im.append(self.axes[ndx].imshow(self.frame[ndx],cmap='gray'))
            self.im[ndx].set_clim(0,255)
            self.axes_xlim = self.axes[ndx].get_xlim()
            self.axes_ylim = self.axes[ndx].get_ylim()
            
            self.droplet_h.append(self.axes[ndx].plot([self.roi[0],self.frmDims[3]],[self.dropY,self.dropY])[0])    
            self.droplet_h[ndx].set_color([0.25,0.25,1])
            self.droplet_h[ndx].set_alpha(0)
            
            cpt = self.roi
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [1,0.25,0.25], linewidth=2, linestyle='-',alpha=0.0)]
            self.thresh_h.append(self.axes[ndx].add_patch(rec[0]))
            self.thresh_h[ndx].set_alpha(0)
            
            
            if self.user_cfg['thresh_info']['axesRef'] == s:
                self.threshAxes = self.axes[ndx]
                self.thresh_h[ndx].set_alpha(0.0)
            if self.user_cfg['droplet_info']['axesRef'] == s:
                self.dropletAxes = self.axes[ndx]
                self.droplet_h[ndx].set_alpha(0.0)
            self.axes[ndx].set_xlim(self.axes_xlim)
            self.axes[ndx].set_ylim(self.axes_ylim)
            
        self.figure.canvas.draw()
        # self.canvas.mpl_connect('button_press_event', self.onClick)
        # self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyPressed)
    
    # def OnKeyPressed(self, event):
    #     # print(event.GetModifiers())
    #     # print(event.GetKeyCode())
    #     enter = False
    #     if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == wx.WXK_NUMPAD_ENTER:
    #         enter = True
    #     if self.set_right.HasFocus() or self.set_left.HasFocus():
    #         if enter:
    #             self.play.SetFocus()
    #         else:
    #             event.Skip()
    #             return
    #     if enter:
    #         if self.set_thresh.GetValue():
    #             ndx = self.axes.index(self.threshAxes)
    #             self.user_cfg['thresh_info']['roiXWYH'] = np.ndarray.tolist(self.roi)
    #             self.user_cfg['thresh_info']['axesRef'] = self.camStrList[ndx]
    #         elif self.set_drop.GetValue():
    #             ndx = self.axes.index(self.dropletAxes)
    #             self.user_cfg['droplet_info']['yVal'] = int(round(self.dropY))
    #             self.user_cfg['droplet_info']['axesRef'] = self.camStrList[ndx]
            
    #         multiCam.write_config(self.user_cfg)
    #         self.set_thresh.SetValue(False)
    #         self.set_drop.SetValue(False)
    #         self.widget_panel.Enable(True)
    #         self.play.SetFocus()
    #     elif event.GetKeyCode() == 314: #LEFT
    #         x = -1
    #         y = 0
    #     elif event.GetKeyCode() == 316: #RIGHT
    #         x = 1
    #         y = 0
    #     elif event.GetKeyCode() == 315: #UP
    #         x = 0
    #         y = -1
    #     elif event.GetKeyCode() == 317: #DOWN
    #         x = 0
    #         y = 1
    #     else:
    #         event.Skip()
            
    #     if self.set_thresh.GetValue():
    #         self.roi[0]+=x
    #         self.roi[2]+=y
    #         self.roi[3] = self.frmDims[1]-self.roi[2]-5
    #         self.dropFindNdcs = np.arange(self.roi[0],self.frmDims[3])
    #         self.dropSums = np.zeros(len(self.dropFindNdcs))
    #         self.drawROI()
    #     elif self.set_drop.GetValue():
    #         self.dropY+=y
    #         self.drawROI()
            
    # def drawROI(self):
    #     if self.set_thresh.GetValue():
    #         ndx = self.axes.index(self.threshAxes)
    #         self.thresh_h[ndx].set_x(self.roi[0])
    #         self.thresh_h[ndx].set_y(self.roi[2])
    #         self.thresh_h[ndx].set_width(self.roi[1])
    #         self.thresh_h[ndx].set_height(self.roi[3])
    #         self.thresh_h[ndx].set_alpha(0.6)
    #         self.droplet_h[ndx].set_xdata([self.roi[0], self.frmDims[3]])
    #     elif self.set_drop.GetValue():
    #         ndx = self.axes.index(self.dropletAxes)
    #         self.droplet_h[ndx].set_ydata([self.dropY, self.dropY])
    #         self.droplet_h[ndx].set_alpha(0.6)
    #     self.figure.canvas.draw()
        
    # def onClick(self,event):
    #     self.user_cfg = multiCam.read_config()
    #     if self.set_thresh.GetValue():
    #         self.threshAxes = event.inaxes
    #         self.roi = np.asarray(self.user_cfg['thresh_info']['roiXWYH'], int)
    #         roi_x = event.xdata
    #         roi_y = event.ydata
    #         self.roi = np.asarray([roi_x,self.roi[1],roi_y,self.roi[3]], int)
    #         self.roi[3] = self.frmDims[1]-self.roi[2]-5
    #         self.dropFindNdcs = np.arange(self.roi[0],self.frmDims[3])
    #         self.dropSums = np.zeros(len(self.dropFindNdcs))
    #     elif self.set_drop.GetValue():
    #         self.dropletAxes = event.inaxes
    #         self.dropY = round(event.ydata)
    #     self.drawROI()
        
    def comFun(self, event):
        evobj = event.GetEventObject()
        if self.big_in == evobj:
            self.ser.write(b'D')
        elif self.big_out == evobj:
            self.ser.write(b'C')
        elif self.air_puff == evobj:
            self.ser.write(b'B')
        elif self.puff_dur == evobj:
            self.user_cfg['puffDur'] = int(self.puff_dur.GetValue())
            multiCam.write_config(self.user_cfg)
            msg = 'A'+str(self.user_cfg['puffDur'])
            self.ser.write(msg.encode())
        elif self.set_left == evobj:
            self.user_cfg['leftVal'] = int(self.set_left.GetValue())
            multiCam.write_config(self.user_cfg)
            msg = 'L'+str(self.user_cfg['leftVal'])
            self.ser.write(msg.encode())
            time.sleep(1)
            msg = 'V'+str(-90)
            self.ser.write(msg.encode())
        elif self.set_right == evobj:
            self.user_cfg['rightVal'] = int(self.set_right.GetValue())
            multiCam.write_config(self.user_cfg)
            msg = 'R'+str(self.user_cfg['rightVal'])
            self.ser.write(msg.encode())
            time.sleep(1)
            msg = 'V'+str(90)
            self.ser.write(msg.encode())
        elif self.angle_set == evobj:
            self.servoAngle = int(self.angle_set.GetValue())
            msg = 'V'+str(self.servoAngle)
            self.ser.write(msg.encode())
        elif self.give_reward == evobj:
            self.ser.write(b'U')
        elif self.step_sz == evobj:
            self.user_cfg['stepSize'] = int(self.step_sz.GetValue())
            multiCam.write_config(self.user_cfg)
            self.user_cfg = multiCam.read_config()
            msg = 'S'+str(self.user_cfg['stepSize'])
            self.ser.write(msg.encode())
            
    def setLines(self, event):
        self.widget_panel.Enable(False)
        
    def compressVid(self, event):
        print('\n\n---- Please DO NOT close this GUI until compression is complete!!! ----\n\n')
        time.sleep(10)
        compressThread = compressVideos.multiCam_compress()
        compressThread.start()
        self.compress_vid.Enable(False)
        
    def camReset(self,event):
        self.camaq.value = 2
        self.initThreads()
        self.startAq()
        time.sleep(3)
        self.stopAq()
        self.deinitThreads()
        print('\n*** CAMERAS RESET ***\n')
        
    def liveFeed(self, event):
        if self.play.GetLabel() == 'Abort':
            self.rec.SetValue(False)
            self.recordCam(event)
            
            if wx.MessageBox("Are you sure?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                shutil.rmtree(self.sess_dir)
            self.play.SetValue(False)
                        
        elif self.play.GetValue() == True:
            if not self.liveTimer.IsRunning():
                self.camaq.value = 1
                self.startAq()
                self.liveTimer.Start(150)
                self.play.SetLabel('Stop')
            
            self.rec.Enable(False)
            for h in self.disable4cam:
                h.Enable(False)
            
        else:
            if self.liveTimer.IsRunning():
                self.liveTimer.Stop()
            self.stopAq()
            time.sleep(2)
            self.play.SetLabel('Live')
            
            self.rec.Enable(True)
            for h in self.disable4cam:
                h.Enable(True)
            
                
    def vidPlayer(self, event):
        if self.camaq.value == 2:
            return
        for ndx, im in enumerate(self.im):
            if self.frmGrab[ndx].value == 1:
                self.frameBuff[ndx][0:] = np.frombuffer(self.array[ndx].get_obj(), self.dtype, self.size)
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.h[ndx], self.w[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                self.frmGrab[ndx].value = 0
                
                
        # ndx = self.axes.index(self.threshAxes)
        # self.maxBack[:,:] = np.minimum(self.frame[ndx],self.imBack)
        # self.frmNoBack[:,:] = np.subtract(self.frame[ndx],self.maxBack)
        # for s, v in enumerate(self.dropFindNdcs):
        #     self.dropSums[s] = np.sum(self.frmNoBack[self.dropY-5:self.dropY+5,v])
        # self.frmNoBack[self.dropY-5:self.dropY+5,v] = 255
        # im.set_data(self.frmNoBack)
        
        self.figure.canvas.draw()
        
        if self.play.GetLabel() == 'Abort':
            if self.auto:
                self.autoEvents()
                
    def autoEvents(self):
        ndx = self.axes.index(self.threshAxes)
        currTime = time.time()
        self.maxBack[:,:] = np.minimum(self.frame[ndx],self.imBack)
        self.frmNoBack[:,:] = np.subtract(self.frame[ndx],self.maxBack)
        for s, v in enumerate(self.dropFindNdcs):
            self.dropSums[s] = np.sum(self.frmNoBack[self.dropY-5:self.dropY+5,v])
        dropSumTest = np.mean(np.sort(self.dropSums)[-10:])
        if dropSumTest > 100:
            dropletPresent = True
        else:
            dropletPresent = False
        
        if self.dropletTest and currTime > self.dropTimer:
            self.dropletTest = False
            if not dropletPresent:
                if self.ser_success:
                    self.ser.write(b'U')
        
        if self.stimiter > len(self.randoAngles)-1:
            np.random.shuffle(self.randoAngles)
            self.stimiter = 0
        
        moveDropper = False
        if currTime > self.minTimer and not dropletPresent:
            moveDropper = True
        elif currTime > self.maxTimer:
            moveDropper = True
        
        handPass = False
        cpt = self.roi
        handBox = self.frmNoBack[ndx][cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
        handBoxTest = np.mean(np.sort(handBox[:])[:self.roi[1]])
        if handBoxTest > 50:
            self.handHistory = currTime+self.reward_delay
        elif currTime > self.handHistory:
            handPass = True
        if not handPass:
            moveDropper = False
        
        if moveDropper:
            # print(np.sort(self.dropSums)[-10:])
            # print(dropSumTest)

            self.dropletTest = True
            self.dropTimer = currTime+2
            self.minTimer = currTime+self.minInterval
            self.maxTimer = currTime+self.maxInterval
            self.handHistory = currTime+self.reward_delay
            self.servoAngle = self.randoAngles[self.stimiter]
            self.stimiter+=1
            self.events.write("%d\t%d\n\r" % (self.servoAngle,self.frmaq.value))
            if self.ser_success:
                msg = 'V'+str(self.servoAngle)
                self.ser.write(msg.encode())
                time.sleep(2)
         
        
        
    def autoCapture(self, event):
        self.sliderTabs+=self.sliderRate
        if self.sliderTabs > self.slider.GetMax():
            self.rec.SetValue(False)
            self.recordCam(event)
            self.slider.SetValue(0)
        else:
            self.slider.SetValue(round(self.sliderTabs))
            self.vidPlayer(event)
            
    def getBack(self, event):
        ndx = self.axes.index(self.threshAxes)
        self.imBack[:,:] = self.frame[ndx]
        self.dropFindNdcs = np.arange(self.thresh_line,self.frmDims[3])
        self.dropSums = np.zeros(len(self.dropFindNdcs))
        
    def recordCam(self, event):
        if self.rec.GetValue():
            
            liveRate = 1000
            self.Bind(wx.EVT_TIMER, self.autoCapture, self.recTimer)
            if int(self.minRec.GetValue()) == 0 and int(self.secRec.GetValue()) == 0:
                self.rec.SetValue(False)
                return
            totTime = int(self.secRec.GetValue())+int(self.minRec.GetValue())*60
            # self.proto_str = self.protocol.GetStringSelection()
            self.proto_str = 'Protocol'
            self.auto = False
            
            if not self.proto_str == 'Protocol':
                proto_name = os.path.join(self.protoDir, self.proto_str + '.yaml')
                ruamelFile = ruamel.yaml.YAML()
                protopath = Path(proto_name)
                if os.path.exists(protopath):
                    try:
                        with open(protopath, 'r') as f:
                            proto_cfg = ruamelFile.load(f)
                    except:
                        print('Failed to open protocol')
                        self.rec.SetValue(False)
                        return
                else:
                    print('Protocol not found')
                    self.rec.SetValue(False)
                    return
                
                
                self.randoAngles = np.linspace(proto_cfg['minimum angle'],proto_cfg['maximum angle'],proto_cfg['location count'])
                np.random.shuffle(self.randoAngles)
                time.sleep(proto_cfg['record delay'])
                self.protoDelay = proto_cfg['protocol delay']
                totTime = proto_cfg['session dur']*60
                self.stimiter = 0
                self.maxInterval = proto_cfg['maximum interval']
                if self.maxInterval == 0:
                    self.maxInterval = np.inf
                self.minInterval = proto_cfg['minimum interval']
                self.roi = np.asarray(self.user_cfg['thresh_info']['roiXWYH'], int)
                self.auto = True
                self.reward_delay = proto_cfg['reward delay']
            else:
                self.auto = False
        
                    
            spaceneeded = 0
            for ndx, w in enumerate(self.aqW):
                recSize = w*self.aqH[ndx]*3*self.recSet[ndx]*totTime
                spaceneeded+=recSize
                
            self.slider.SetMax(100)
            self.slider.SetMin(0)
            self.slider.SetValue(0)
            self.sliderTabs = 0
            self.sliderRate = 100/(totTime/(liveRate/1000))
            
            date_string = datetime.datetime.now().strftime("%Y%m%d")
            base_dir = os.path.join(self.user_cfg['raw_data_dir'], date_string, self.user_cfg['unitRef'])
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            freespace = shutil.disk_usage(base_dir)[2]
            if spaceneeded > freespace:
                dlg = wx.MessageDialog(parent=None,message="There is not enough disk space for the requested duration.",
                                       caption="Warning!", style=wx.OK|wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()
                self.rec.SetValue(False)
                return
            prev_expt_list = [name for name in os.listdir(base_dir) if name.startswith('session')]
            file_count = len(prev_expt_list)+1
            sess_string = '%s%03d' % ('session', file_count)
            self.sess_dir = os.path.join(base_dir, sess_string)
            if not os.path.exists(self.sess_dir):
                os.makedirs(self.sess_dir)
            multiCam.read_metadata
            self.meta,ruamelFile = multiCam.metadata_template()
            self.meta['unitRef']=self.user_cfg['unitRef']
            self.meta['duration (s)']=totTime
            self.meta['ID']=self.expt_id.GetValue()
            # self.meta['odor']=self.odor_id.GetValue()
            self.meta['placeholderA']='info'
            self.meta['placeholderB']='info'
            self.meta['Designer']='name'
            self.meta['Stim']='none'
            self.meta['StartTime']=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.meta['Collection']='info'
            meta_name = '%s_%s_%s_metadata.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
            self.metapath = os.path.join(self.sess_dir,meta_name)
            
            usrdatadir = os.path.dirname(os.path.realpath(__file__))
            configname = os.path.join(usrdatadir, 'userdata.yaml')
            copyname = '%s_%s_%s_userdata_copy.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
            shutil.copyfile(configname,os.path.join(self.sess_dir,copyname))
            if not self.proto_str == 'Protocol':
                self.meta['Stim']=self.proto_str
                copyname = '%s_%s_%s_protocol.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
                protopath = Path(proto_name)
                shutil.copyfile(protopath,os.path.join(self.sess_dir,copyname))
                
            for ndx, s in enumerate(self.camStrList):
                camID = str(self.user_cfg[s]['serial'])
                name_base = '%s_%s_%s_%s' % (date_string, self.user_cfg['unitRef'], sess_string, self.user_cfg[s]['nickname'])
                path_base = os.path.join(self.sess_dir,name_base)
                self.camq[camID].put('recordPrep')
                self.camq[camID].put(path_base)
                self.camq_p2read[camID].get()
                
            for h in self.disable4cam:
                h.Enable(False)
            
            if not self.recTimer.IsRunning():
                self.camaq.value = 1
                self.startAq()
                self.recTimer.Start(liveRate)
                
            self.rec.SetLabel('Stop')
            self.play.SetLabel('Abort')
            
            if self.auto:
                self.minTimer = time.time()+self.protoDelay
                self.maxTimer = time.time()+self.protoDelay
                self.handHistory = time.time()+self.reward_delay
                self.dropletTest = False
                self.dropTimer = time.time()+2
                eventsname = '%s_%s_%s_events.txt' % (date_string, self.user_cfg['unitRef'], sess_string)
                self.events = open(os.path.join(self.sess_dir,eventsname), 'w')
        else:
            self.meta['duration (s)']=round(self.meta['duration (s)']*(self.sliderTabs/100))
            multiCam.write_metadata(self.meta, self.metapath)
            if self.auto:
                self.events.close()
                self.auto = False
                            
            if self.recTimer.IsRunning():
                self.recTimer.Stop()
            self.stopAq()
            time.sleep(2)
            self.rec.SetLabel('Record')
            self.play.SetLabel('Play')
            # if self.compressThread.is_alive():
            #     print('\n\n---- Waiting for compression to complete! ----\n\n')
            #     while self.compressThread.is_alive():
            #         time.sleep(10)
            # self.compressThread.terminate()   
            # self.compressThread = compressVideos.multiCam_compress()
            # self.compressThread.start()

            
            # if not self.mv.is_alive():
            #     self.mv.terminate()   
            #     self.mv = multiCam.moveVids()
            #     self.mv.start()
            
            
            # compressThread = compressVideos.multiCam_compress()
            # compressThread.start()
            self.slider.SetValue(0)
            ndx = self.axes.index(self.threshAxes)
            
            for h in self.disable4cam:
                h.Enable(True)
            
            
    
    def initThreads(self):
        self.camq = dict()
        self.camq_p2read = dict()
        self.cam = list()
        for ndx, camID in enumerate(self.camIDlist):
            self.camq[camID] = Queue()
            self.camq_p2read[camID] = Queue()
            self.cam.append(spin.Run_Cams(self.camq[camID], self.camq_p2read[camID],
                                               self.array[ndx], self.frmGrab[ndx], camID, self.camIDlist,
                                               self.frmDims, self.camaq, self.frmaq))
            self.cam[ndx].start()
        
        self.camq[self.masterID].put('InitM')
        self.camq_p2read[self.masterID].get()
        for s in self.slist:
            self.camq[s].put('InitS')
            self.camq_p2read[s].get()
            
    def deinitThreads(self):
        for n, camID in enumerate(self.camIDlist):
            self.camq[camID].put('Release')
            self.camq_p2read[camID].get()
            self.camq[camID].close()
            self.camq_p2read[camID].close()
            self.cam[n].terminate()
            
    def startAq(self):
        self.camq[self.masterID].put('Start')
        for s in self.slist:
            self.camq[s].put('Start')
        self.camq[self.masterID].put('TrigOff')
        
    def stopAq(self):
        self.camaq.value = 0
        for s in self.slist:
            self.camq[s].put('Stop')
            self.camq_p2read[s].get()
        self.camq[self.masterID].put('Stop')
        self.camq_p2read[self.masterID].get()
        
    def updateSettings(self, event):
        self.user_cfg = multiCam.read_config()
        self.aqW = list()
        self.aqH = list()
        self.recSet = list()
        for n, camID in enumerate(self.camIDlist):
            try:
                self.camq[camID].put('updateSettings')
                self.recSet.append(self.camq_p2read[camID].get())
                self.aqW.append(self.camq_p2read[camID].get())
                self.aqH.append(self.camq_p2read[camID].get())
            except:
                print('\nTrying to fix.  Please wait...\n')
                self.deinitThreads()
                self.camReset(event)
                self.initThreads()
                self.camq[camID].put('updateSettings')
                self.recSet.append(self.camq_p2read[camID].get())
                self.aqW.append(self.camq_p2read[camID].get())
                self.aqH.append(self.camq_p2read[camID].get())
            
    def initCams(self, event):
        if self.init.GetValue() == True:
            self.Enable(False)
            self.ser_success = False
            # try:
            #     try:
            #         self.ser = serial.Serial(self.user_cfg['COM'], baudrate=115200)
            #     except:
            #         self.ser = serial.Serial('/dev/ttyACM1', baudrate=115200)
            #     self.ser_success = True
            #     for h in self.serHlist:
            #         h.Enable(True)
            #     self.user_cfg['leftVal'] = int(self.set_left.GetValue())
            #     msg = 'L'+str(self.user_cfg['leftVal'])
            #     self.ser.write(msg.encode())
            #     self.user_cfg['rightVal'] = int(self.set_right.GetValue())
            #     time.sleep(1)
            #     msg = 'R'+str(self.user_cfg['rightVal'])
            #     self.ser.write(msg.encode())
            #     time.sleep(1)
            #     msg = 'V'+str(0)
            #     self.ser.write(msg.encode())
            # except:
            #     self.ser_success = False
            #     if not self.user_cfg['COM'] == 'none':
            #         print('\n!!! Serial connection failed !!!\n')
                
            self.colormap = plt.get_cmap('jet')
            self.colormap = self.colormap.reversed()
            self.markerSize = 6
            self.alpha = 0.7
            
            self.initThreads()
            self.updateSettings(event)
            
            self.Bind(wx.EVT_TIMER, self.vidPlayer, self.liveTimer)
            
            self.camaq.value = 1
            self.startAq()
            time.sleep(1)
            self.camaq.value = 0
            self.stopAq()
            self.x1 = list()
            self.x2 = list()
            self.y1 = list()
            self.y2 = list()
            self.h = list()
            self.w = list()
            self.dispSize = list()
            self.imBack = np.zeros(self.shape,'ubyte')
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                self.frameBuff[ndx][0:] = np.frombuffer(self.array[ndx].get_obj(), self.dtype, self.size)
                self.h.append(self.frmDims[1])
                self.w.append(self.frmDims[3])
                self.y1.append(self.frmDims[0])
                self.x1.append(self.frmDims[2])
                self.dispSize.append(self.h[ndx]*self.w[ndx])
                self.y2.append(self.y1[ndx]+self.h[ndx])
                self.x2.append(self.x1[ndx]+self.w[ndx])
                
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.h[ndx], self.w[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                
                # if self.threshAxes == self.axes[ndx]:
                #     self.thresh_h[ndx].set_alpha(0.6)
                #     self.droplet_h[ndx].set_alpha(0.6)
                        
            self.figure.canvas.draw()
            
            self.init.SetLabel('Release')
            self.reset.Enable(False)
            for h in self.onWhenCamEnabled:
                h.Enable(True)
                
            self.Enable(True)
        else:
            # for h in self.serHlist:
            #     h.Enable(False)
            # if self.ser_success:
            #     self.ser.write(b'X')
            #     self.ser.close()
        
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                im.set_data(self.frame[ndx])
                if self.threshAxes == self.axes[ndx]:
                    self.thresh_h[ndx].set_alpha(0.0)
                    self.droplet_h[ndx].set_alpha(0.0)
                
            self.figure.canvas.draw()
            
            self.init.SetLabel('Enable')
            self.reset.Enable(True)
            for h in self.onWhenCamEnabled:
                h.Enable(False)

            self.deinitThreads()
            
    def quitButton(self, event):
        """
        Quits the GUI
        """
        print('Close event called')
        if self.play.GetValue():
            self.play.SetValue(False)
            self.liveFeed(event)
        if self.rec.GetValue():
            self.rec.SetValue(False)
            self.recordCam(event)
        if self.init.GetValue():
            self.init.SetValue(False)
            self.initCams(event)
        # if self.mv.is_alive():
        #     print('\n\n---- Waiting for file transfer to complete! ----\n\n')
        #     while self.mv.is_alive():
        #         time.sleep(10)
        # self.mv.terminate()   
        try:
            if self.compressThread.is_alive():
                print('\n\n---- Waiting for compression to complete! ----\n\n')
                while self.compressThread.is_alive():
                    time.sleep(10)
            self.compressThread.terminate()   
        except:
            pass
        
        self.statusbar.SetStatusText("")
        self.Destroy()
    
def show():
    app = wx.App()
    MainFrame(None).Show()
    app.MainLoop()

if __name__ == '__main__':
    user_cfg = multiCam.read_config()
    if user_cfg['cam1'] == None:
        print('Camera serial numbers are missing')
    else:
        show()