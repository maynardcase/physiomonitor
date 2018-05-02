#!/usr/bin/env python

# Aim is to listen for a noise corresponding to a blow in to a physio tube.
# This should have a duration of about three seconds followed by a pause.
# The volume of the noise should roughly correspond to the power of the blow (to be confirmed)
# When a pause is detected, increment the count. We aim to get N blows (e.g. 10 / 12)
# When all blows are detected, celebrate in some way and reset the count (but increment the set count)
# When we get to N sets, celebrate in a big way

# Problems to solve
# a) listening to blowing noise from USB microphone
# b) detecting absence of blowing noise (need to process to remove background noise)
# c) visualising blowing noise on Unicorn HAT
# d) celebration animations(!)

import alsaaudio as aa
import audioop
from time import sleep
from collections import deque
import time
import select
import sys
import math
import random

import unicornhat as unicorn
from UHScroll import *

print aa.pcms(aa.PCM_CAPTURE)

# Set up audio
data_in = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NONBLOCK, device='default:CARD=Device')
data_in.setchannels(2)
data_in.setrate(44100)
data_in.setformat(aa.PCM_FORMAT_S16_LE)
data_in.setperiodsize(256)

# Set up tracking variables
circular_queue = deque([1,2], maxlen=20)
warmup = 0
queue_total = 0
blowing = False
blowcount = 0
setcount = 0
sidecount = 0
blows_per_set = 12
sets_per_side = 6
total_sides = 3
lastBlowDuration = 0
currentBlowDuration = 0
lastScaledVolAverage = 0
name= "Thomas"
motivations = [
    "Go {0} go!",
    "Great blows {0}!",
    "Good effort {0}!",
    "{0}, you're on fire!",
    "{0} is amazing!",
    "That was fantastic!",
    "Good progress {0}!",
    "Physio star {0}!",
    "Gold star for {0}!",
    "You are doing great {0}!",
    "Awesome physio {0}!",
    "Keep it up {0}!",
    "Great work {0}!",
    "Super strong {0}!",
    "Your blows are powerful!"
]
unicorn_height, unicorn_width = unicorn.get_shape()

# Set up Unicorn HAT
unicorn.set_layout(unicorn.AUTO)
unicorn.rotation(0)
unicorn.brightness(0.5)
width,height=unicorn.get_shape()

# Non-blocking IO
def heardEnter():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            input = sys.stdin.readline()
            if input == '\n':
                return -1
            if input == ' ':
                return +1
            else:
                return 0
    return False

def getMotivation(name):
    return random.choice(motivations).format(name)

def draw(totalblows):
    blows = totalblows % blows_per_set
    sides = int(math.floor(totalblows / (blows_per_set * sets_per_side)))
    sets = int(math.floor(totalblows / blows_per_set) - (sides * sets_per_side))

    # Clear output area
    for x in range (4,8):
        for y in range (0,8):
            unicorn.set_pixel(x,y, 0,0,0)

    # Draw the sides
    for s in range(0,sides):
        unicorn.set_pixel(7, s, 0, 0, 255)

    # Draw the sets
    for s in range(0,sets):
        if s==0:
            unicorn.set_pixel(6, s, 255, 51, 0)
        elif s==1:
            unicorn.set_pixel(6, s, 255, 255, 102)
        elif s==2:
            unicorn.set_pixel(6, s, 102, 255, 102)
        elif s==3:
            unicorn.set_pixel(6, s, 0, 153, 255)
        elif s==4:
            unicorn.set_pixel(6, s, 255, 102, 255)
        elif s==5:
            unicorn.set_pixel(6, s, 255, 51, 0)
        else:
            unicorn.set_pixel(6, s, 255, 51, 0)




    # Draw the blows
    for s in range(0, blows):
        # Number of blows can be > 7 so we need to
        if (s < unicorn_height):
            unicorn.set_pixel(5, s, 255, 255, 255)
        else:
            unicorn.set_pixel(4, s % unicorn_height, 255, 255, 255)

    unicorn.show()

def getInterpolatedRGB(r1, g1, b1, r2, g2, b2, min, max, value):
    if value > max:
        value = max
    if value < min:
        value = min

    range = max - min
    # Get ratio of 0-1 for source value
    valratio = (value - min) / range

    if (r2 > r1):
        rx = int(((r2 - r1) * valratio) + r1)
    else:
        rx = int(((r1 - r2) * valratio) + r2)

    if (g2 > g1):
        gx = int(((g2 - g1) * valratio) + g1)
    else:
        gx = int(((g1 - g2) * valratio) + g2)

    if (b2 > b1):
        bx = int(((b2 - b1) * valratio) + b1)
    else:
        bx = int(((b1 - b2) * valratio) + b2)

    print "Interpolated RGB: value {0} between {1} and {2} with range {3} gives a ratio of {4}. So if r1 is {5} and r2 is {6} then x is {7},{8},{9}".format(value, min, max, range, valratio, r1, r2, rx, gx, bx)

    return (rx, gx, bx)

while True:
        # Read data from device
        l,data = data_in.read()
        if l:
                # catch frame error
                try:

                        max_vol=audioop.max(data,2)
                        scaled_vol = max_vol//4680

                        # Add the current volume to the circular queue
                        circular_queue.append(scaled_vol)
                        # Don't bother scaling for the first 20 data points
                        if (warmup < 20):
                            warmup = warmup + 1
                            queue_total = queue_total + scaled_vol
                        else:
                            # Remove oldest value
                            old_vol=circular_queue.popleft()
                            # Keep total up to date
                            queue_total = queue_total + scaled_vol - old_vol
                            # Get average value
                            scaled_vol_average = queue_total / 19
                            # Display the current value from 0-7 on the unicorn HAT
                            currentTime = time.time()

#                            (r, g, b) = getInterpolatedRGB(0, 0, 0, 255, 255, 255, 0, 2, currentBlowDuration)
#                            print r, g, b, currentBlowDuration
                            for i in range(0, scaled_vol_average+1):
                                unicorn.set_pixel(0, i, 0, 255, 0)
                            # Clear any previously set pixels (if volume is going down)
                            if (lastScaledVolAverage > scaled_vol_average):
                                for y in range(scaled_vol_average+1, lastScaledVolAverage+1):
                                    unicorn.set_pixel(0, y, 0, 0, 0)
                            unicorn.show()
                            lastScaledVolAverage = scaled_vol_average

                            # Have we received keyboard input? If so it means we need to remove a blow
                            keyInput = heardEnter();
                            if (keyInput != False and blowcount > 0):
                                blowcount = blowcount + keyInput
                                draw(blowcount)

                            # Keep track of the number of blows and the duration
                            if (blowing == False and scaled_vol_average > 2.8):
                                startBlowingTime = time.time()
                                blowing = True
                                blowcount = blowcount + 1
                            if (blowing == True and scaled_vol_average <= 0.3):
                                stopBlowingTime = time.time()
                                lastBlowDuration = stopBlowingTime - startBlowingTime
                                currentBlowDuration = lastBlowDuration
                                blowing = False
                                if blowcount % (blows_per_set * sets_per_side) == 0:
                                    unicorn_scroll(getMotivation(name), 'white', 255, 0.09)
                                    # Unicorn scroll has its own idea about the correct orientation, so change back to 0
                                    unicorn.rotation(0)
                                draw(blowcount)
                            elif (blowing == True):
                                currentBlowDuration = currentTime - startBlowingTime



                            print "Scaled vol: {0}\told_vol: {1}\t scaled_vol_average: {2}\tblowing: {3}\tblowcount: {4}\tsetcount: {5}\tsidecount: {6}\tlastBlowDuration: {7}".format(scaled_vol, old_vol, scaled_vol_average, blowing, blowcount, setcount, sidecount, lastBlowDuration)


                except audioop.error, e:
                        if e.message !="not a whole number of frames":
                                raise e


