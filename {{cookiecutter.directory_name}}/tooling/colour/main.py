#!/bin/python3.6
# TODO: move this colour stuff into another file
# just to make things more neat and managable
class colours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def emph(txt):
    return colours.HEADER + txt + colours.ENDC

# returns a string wrapped in characters to colour this
# as a warning colour
def warn(txt):
    return colours.WARNING + txt + colours.ENDC

# returns a string wrapped in characters to colour this
# as a error colour
def err(txt):
    return colours.FAIL + txt + colours.ENDC

error = err

# returns a string wrapped in characters to colour this
# as a pass (green) colour
# this function is not called 'pass', because that's a protected phrase
def good(txt):
    return colours.OKGREEN + txt + colours.ENDC
