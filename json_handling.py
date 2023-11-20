import json
import numpy as np 
import csv

# functions for processing/analysing the json data 

def openjson(path): # opens a json and reads the info into a dictionary
    with open(path, 'r') as j:
        info = json.loads(j.read())
    return info

def tempo(path): # reads the BPM information from json file
    info = openjson(path)
    bpm = info["tempo"]
    return int(bpm)

def beats(path): # reads the beats information (in seconds) from json
    info = openjson(path)
    beats = info["beats"]
    return beats

def beatseek(percentage, path, fs): # given a percentage (samples), outputs the index from beat array
    beats_array = np.asarray(beats(path))
    beats_array = beats_array * fs    
    i = np.abs(beats_array - percentage).argmin()
    return i

def mouse_quantizetobeats(path, position, song_length, width): # given a position, outputs a position in line with beats info
    beats_array = np.asarray(beats(path))
    beats_array = (beats_array/song_length)*width 
    index = (np.abs(beats_array - position)).argmin()
    return beats_array[index]

def segmentation(path): # outputs segmentation data array (time in sec) from json  
    info = openjson(path)
    segmentation_array = info["segmentation"]
    extracted_seg = []
    for array in segmentation_array:
        extracted_seg = np.append(extracted_seg,array[0])
    return extracted_seg

def plot_segmentation(path, fs, kernel): # outputs an array with segmentation scaled to plot width
    extracted_seg = segmentation(path)
    plotting_segs = []
    for i in extracted_seg:
        i *= fs
        i = int(i/kernel)
        final = np.append(plotting_segs,i)
    return plotting_segs

def segmentation_beats(path): # uses segmentation data to output 2 arrays of closest beats and their indexes
    beats_array = np.asarray(beats(path))
    segmentation_array = np.asarray(segmentation(path))
    segmentation_closest_beats = []
    indexes = []
    for i in segmentation_array:
        index = np.abs(beats_array - i).argmin()
        indexes = np.append(indexes,index)
        segmentation_closest_beats = np.append(segmentation_closest_beats, beats_array[index])
    return segmentation_closest_beats,indexes