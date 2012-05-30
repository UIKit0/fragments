import sys

GREY    = 90
RED     = 91
GREEN   = 92
YELLOW  = 93
BLUE    = 94
MAGENTA = 95
CYAN    = 96
WHITE   = 97


def colorize(line, color=None, colorblind=False):
    color_by_prefix = {
        '+' : BLUE if colorblind else GREEN,
        '-' : RED    ,
        '@' : MAGENTA,
        '?' : MAGENTA,
        'M' : YELLOW ,
        'D' : RED    ,
        'A' : BLUE if colorblind else GREEN,
        'E' : GREY   ,
    }
    if color is None:
        color = color_by_prefix.get(line[0:1])
    if sys.stdout.isatty() and color:
        return '\033[%sm%s\033[0m' % (color, line)
    else:
        return line
