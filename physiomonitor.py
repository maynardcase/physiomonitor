#!/usr/bin/env python

# Aim is to listen for a noise corresponding to a blow in to a physio tube.
# This should have a duration of about three seconds followed by a pause.
# The volume of the noise should roughly correspond to the power of the blow (to be confirmed)
# When a pause is detected, increment the count. We aim to get N blows (e.g. 10 / 12)
# When all blows are detected, celebrate in some way and reset the count (but increment the set count)
# When we get to N sets, celebrate in a big way

import alsaaudio as aa
import audioop
from time import sleep
from collections import deque
import time
import select
import sys
import math
import random
import argparse

import unicornhat as unicorn
from UHScroll import *

print (aa.pcms(aa.PCM_CAPTURE))

# Set up audio
data_in = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NONBLOCK, device='default:CARD=Device')
data_in.setchannels(2)
data_in.setrate(44100)
data_in.setformat(aa.PCM_FORMAT_S16_LE)
data_in.setperiodsize(256)

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
def heard_enter():
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

def get_motivation(name):
    return random.choice(motivations).format(name)

def draw(totalblows,blows_per_set,sets_per_side):
    blows = totalblows % blows_per_set
    sides = int(math.floor(totalblows / (blows_per_set * sets_per_side)))
    sets = int(math.floor(totalblows / blows_per_set) - (sides * sets_per_side))

    clear_output()

    draw_sides(sides)

    draw_sets(sets)

    draw_blows(blows)


    unicorn.show()


def draw_blows(blows):
    # Draw the blows
    for s in range(0, blows):
        # Number of blows can be > 7 so we need to
        if (s < 4):
            unicorn.set_pixel(5, s, 255, 255, 255)
        elif (s >= 4 and s < 8):
            unicorn.set_pixel(4, s % 4, 255, 255, 255)
        else:
            unicorn.set_pixel(3, s % 8, 255, 255, 255)


def draw_sets(sets):
    # Draw the sets
    for s in range(0, sets):
        if s == 0:
            unicorn.set_pixel(6, s, 255, 51, 0)
        elif s == 1:
            unicorn.set_pixel(6, s, 255, 153, 51)
        elif s == 2:
            unicorn.set_pixel(6, s, 255, 255, 102)
        elif s == 3:
            unicorn.set_pixel(6, s, 102, 255, 102)
        elif s == 4:
            unicorn.set_pixel(6, s, 0, 153, 255)
        elif s == 5:
            unicorn.set_pixel(6, s, 153, 51, 255)
        else:
            unicorn.set_pixel(6, s, 255, 51, 0)


def draw_sides(sides):
    # Draw the sides
    for s in range(0, sides):
        unicorn.set_pixel(7, s, 0, 0, 255)


def clear_output():
    # Clear output area
    for x in range(2, 8):
        for y in range(0, 8):
            unicorn.set_pixel(x, y, 0, 0, 0)


def get_interpolated_rgb(r1, g1, b1, r2, g2, b2, min, max, value):
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

    print("Interpolated RGB: value {0} between {1} and {2} with range {3} gives a ratio of {4}. "
          "So if r1 is {5} and r2 is {6} then x is {7},{8},{9}".format(value, min, max, range,
                                                                       valratio, r1, r2, rx, gx, bx))

    return (rx, gx, bx)


def main(args):
    # Set up tracking variables
    circular_queue = deque([1, 2], maxlen=20)
    warmup = 0
    blowing = False
    blowcount = args.start # Default to zero
    blows_per_set = 12
    sets_per_side = 6
    last_blow_duration = 0
    current_blow_duration = 0
    last_scaled_vol_average = 0
    queue_total = 0
    name = "Thomas"
    dur = 0

    # If we have overridden the number of blows done this will set up the UI correctly
    draw(blowcount, blows_per_set, sets_per_side)

    while True:
        # Read data from device
        l, data = data_in.read()
        if l:
            # catch frame error
            try:

                max_vol = audioop.max(data, 2)
                scaled_vol = max_vol // 4680

                # Add the current volume to the circular queue
                circular_queue.append(scaled_vol)
                # Don't bother scaling for the first 20 data points
                if (warmup < 20):
                    warmup = warmup + 1
                    queue_total = queue_total + scaled_vol
                else:
                    # Remove oldest value
                    old_vol = circular_queue.popleft()
                    # Keep total up to date
                    queue_total = queue_total + scaled_vol - old_vol
                    # Get average value
                    scaled_vol_average = queue_total / 19

                    # (r, g, b) = getInterpolatedRGB(0, 0, 0, 255, 255, 255, 0, 2, current_blow_duration)
                    #  print r, g, b, current_blow_duration

                    # Display the current value from 0-7 on the unicorn HAT
                    for i in range(0, scaled_vol_average + 1):
                        unicorn.set_pixel(0, i, 0, 255, 0)
                    # Clear any previously set pixels (if volume is going down)
                    if (last_scaled_vol_average > scaled_vol_average):
                        for y in range(scaled_vol_average + 1, last_scaled_vol_average + 1):
                            unicorn.set_pixel(0, y, 0, 0, 0)
                    # Clear out the previous blow duration (if required)
                    if (current_blow_duration < dur):
                        for i in range(0, 6):
                            unicorn.set_pixel(7 - i, 7, 0, 0, 0)
                    dur = current_blow_duration;
                    if dur > 3:
                        dur = 3
                    scaled_dur = int(dur * 2)
                    # Display the current blow duration
                    for i in range(0, scaled_dur):
                        if i == 0:
                            (r, g, b) = (255, 0, 0)
                        elif i == 1:
                            (r, g, b) = (255, 153, 51)
                        elif i == 2:
                            (r, g, b) = (128, 255, 0)
                        elif i == 3:
                            (r, g, b) = (0, 255, 0)
                        elif i == 4:
                            (r, g, b) = (255, 153, 51)
                        elif i == 5:
                            (r, g, b) = (255, 0, 0)

                        unicorn.set_pixel(7 - i, 7, r, g, b)
                    unicorn.show()
                    last_scaled_vol_average = scaled_vol_average

                    # Have we received keyboard input? If so it means we need to remove a blow
                    key_input = heard_enter();
                    if (key_input != False and blowcount > 0):
                        blowcount = blowcount + key_input
                        draw(blowcount,blows_per_set,sets_per_side)

                    # Keep track of the number of blows and the duration
                    if (blowing == False and scaled_vol_average > 2.8):
                        start_blowing_time = time.time()
                        blowing = True
                        blowcount = blowcount + 1
                    if (blowing == True and scaled_vol_average <= 0.3):
                        stop_blowing_time = time.time()
                        last_blow_duration = stop_blowing_time - start_blowing_time
                        current_blow_duration = last_blow_duration
                        blowing = False
                        if blowcount % (blows_per_set * sets_per_side) == 0:
                            unicorn_scroll(get_motivation(name), 'white', 255, 0.09)
                            # Unicorn scroll has its own idea about the correct orientation, so change back to 0
                            unicorn.rotation(0)
                        draw(blowcount,blows_per_set,sets_per_side)
                    if (blowing == True):
                        current_blow_duration = time.time() - start_blowing_time

                    print ("Scaled vol: {0}\told_vol: {1}\t scaled_vol_average: {2}\tblowing: {3}\t" \
                          "blowcount: {4}\tlast_blow_duration: {5}".format(
                        scaled_vol, old_vol, scaled_vol_average, blowing, blowcount, last_blow_duration))


            except audioop.error, e:
                if e.message != "not a whole number of frames":
                    raise e


parser = argparse.ArgumentParser(description='Physio monitor')
parser.add_argument('-s','--start',dest='start',default=0,type=int,help='Number of blows to start from')
parser_results=parser.parse_args()

main(parser_results)



