#!/opt/local/bin/python
#
# Load a single video frame from an image file
# - optional border trim border argument
#
# USAGE : geetee_TestFrame.py <Test Frame Image>
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech
# DATES  : 2014-05-07 JMT From scratch
#
# This file is part of geetee.
#
#    geetee is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    geetee is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#   along with geetee.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014 California Institute of Technology.

import os
import cv2
import numpy as np
import ConfigParser

import mrclean
import pupilometry


def LoadVideoFrame(v_in, config):
    """
    Load and preprocess a single frame from a video stream
    
    Parameters
    ----------
    v_in : opencv video stream
        video input stream
    scale : float
        downsampling scale factor [1.0]
    border : int
        pixel border width to strip
    rotate : int
        rotation in
        
    Returns
    ----
    status : boolean
        Completion status.
    fr : numpy uint8 array
        Preprocessed video frame.
    artifacts : boolean
        Artifact presence in frame.
    """
    
    # Extract config parameters
    downsampling = config.getfloat('VIDEO', 'downsampling')
    border = config.getint('VIDEO', 'border')
    do_mrclean = config.getboolean('VIDEO', 'mrclean')
    
    # Init artifact flag for this frame
    artifact = False    
    
    status, fr = v_in.read()
    
    if status:
        
        # Convert to grayscale
        fr = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY)
        
        # Trim border first
        fr = TrimBorder(fr, border)
        
        # Apply optional MR artifact suppression
        if do_mrclean:
            fr, artifact = mrclean.MRClean(fr)

        # Get trimmed frame size
        nx, ny = fr.shape[1], fr.shape[0]
        
        # Calculate downsampled matrix
        nxd, nyd = int(nx/downsampling), int(ny/downsampling)
        
        # Downsample
        fr = cv2.resize(fr, (nxd, nyd))
        
        # Gaussian blur
        fr = cv2.GaussianBlur(fr, (3,3), 1.0)

        # Robust rescale to 5th, 95th percentile
        fr = pupilometry.RobustRescale(fr, (1,99))
        
    return status, fr, artifact


def TrimBorder(frame, border = 0):
    """
    Trim video frame border introduced by frame capture
    
    Parameters
    ----------
    frame : numpy uint8 array
        video frame
    border : integer
        border width in pixels to strip [0]
        
    Returns
    -------
    frame : numpy unit8 array
        video frame without border
    """
    
    if border > 0:
        
        # Get image dimension
        nx, ny = frame.shape[1], frame.shape[0]
        
        # Set bounding box
        x0 = border
        y0 = border
        x1 = nx - border
        y1 = ny - border
        
        # Make sure bounds are inside image
        x0 = x0 if x0 > 0 else 0
        x1 = x1 if x1 < nx else nx-1
        y0 = y0 if y0 > 0 else 0
        y1 = y1 if y1 < ny else ny-1
        
        # Crop and return
        return frame[y0:y1, x0:x1]
        
    else:
        
        return frame


def LoadImage(image_file, border=0):
    """
    Load an image from a file and strip the border.

    Parameters
    ----------
    image_file : string
        File name of image
    border : integer
        Pixel width of border to strip [0].
        

    Returns
    -------
    frame : 2D numpy array
        Grayscale image array.

    Examples
    --------
    >>> img = LoadImage('test.png', 5)
    """

    # Initialize frame
    frame = np.array([])

    # load test frame image
    try:
        frame = cv2.imread(image_file)
    except:
        print('Problem opening %s to read' % image_file)
        return frame
        
    # Convert to grayscale image if necessary
    if frame.shape[2] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Trim border (if requested)
    frame = TrimBorder(frame, border)
    
    return frame


def LoadConfig(data_dir, subjsess):
    """
    Load ET pipeline configuration parameters
    
    Check first for a global configuration in the root directory,
    then for a specific configuration in the subject/session directory.
    The subj/sess config has precedence.
    
    Arguments
    ----
    root_dir : string
        Root directory containing videos subdir.
    subjsess_dir : string
        Subject/Session subdirectory.
        
    Returns
    ----
    config : config object (see ConfigParser package)
        Configuration object.
    """
    
    # Root config filename
    root_cfg_file = os.path.join(data_dir, 'geetee.cfg')
    
    # Subject/Session config filename
    ss_dir = os.path.join(data_dir, subjsess)
    ss_cfg_file = os.path.join(ss_dir, 'geetee.cfg')
    
    # Create a new parser
    config = ConfigParser.ConfigParser()
    
    # Check first for subject/session config
    if os.path.isfile(ss_cfg_file):
        
        # Load existing subj/sess config file
        config.read(ss_cfg_file)

    elif os.path.isfile(root_cfg_file):
        
        # Load existing root config file
        config.read(root_cfg_file)
        
    else:

        # Write a new default root config file
        config = InitConfig(config)
        with open(root_cfg_file,'wb') as cfg_stream:
            config.write(cfg_stream)
            cfg_stream.close()
            
    return config
   

def InitConfig(config):
    
    # Add video defaults
    config.add_section('VIDEO')
    config.set('VIDEO','inputextension','.mpg')
    config.set('VIDEO','outputextension','.mov')
    config.set('VIDEO','downsampling','4')
    config.set('VIDEO','border','16')
    config.set('VIDEO','rotate','False')
    config.set('VIDEO','mrclean','True')
    
    config.add_section('RANSAC')
    config.set('RANSAC','maxiterations','5')
    config.set('RANSAC','maxrefinements','3')
    config.set('RANSAC','maxinlierperc','95')
    
    config.add_section('LBP')
    config.set('LBP','strictness','40')
    
    config.add_section('CALIBRATION')
    config.set('CALIBRATION','calibrate','False')
    config.set('CALIBRATION','targetx','0.5, 0.1, 0.9, 0.1, 0.1, 0.5, 0.1, 0.9, 0.5')
    config.set('CALIBRATION','targety','0.5, 0.9, 0.9, 0.1, 0.9, 0.9, 0.5, 0.5, 0.1')

    config.add_section('OUTPUT')
    config.set('OUTPUT','verbose','False')
    config.set('OUTPUT','graphics','False')
    
    return config
    
#
# Pupilometry CSV IO
#
def ReadPupilometry(pupils_csv):
    
    return np.genfromtxt(pupils_csv, delimiter = ',', unpack = True)
    
#
# Safe mkdir - from http://code.activestate.com/recipes/82465-a-friendly-mkdir/
#
def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with same name as desired dir ('%s') already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)