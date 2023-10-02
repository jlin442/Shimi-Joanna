import json
import numpy as np 

path = 'Closer.json'

def tempo(input):
    with open(path, 'r') as j:
        info = json.loads(j.read())
    bpm = info["tempo"]
    return int(bpm)

def beatseek(percentage):
    with open(path, 'r') as j:
        info = json.loads(j.read())
    beats = info["beats"]
    beatslist = np.asarray(beats)
    beatslist = beatslist / max(beatslist)
    i = (np.abs(beatslist - percentage)).argmin()
    return beatslist[i]

p = beatseek(0.444444)
print (p)


# segmentation(start or end of each segment): 
# 2d array [[time_stamp0, energy0],[time_stamp1, energy1]...[]] 

# verticals(selected onsets): 
# 2d array [[time_stamp0, energy0],[time_stamp1, energy1]...[]]

# beats(record tempo in a list format) : suppose the tempo is 60, then the list can be: 
# [0, 1, 2, 3....]

# tempo: a float that represent tempo



    


