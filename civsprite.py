#!/usr/bin/env python3.8

import argparse
import sys

import sprite.format.spr
import sprite.format.txt
import sprite.format.xml


def _input_format(name):
    input_formats = {
        'spr': sprite.format.spr.load,
        'txt': sprite.format.txt.load,
        'xml': sprite.format.xml.load
    }
    split_name = name.rsplit('.', 1)
    if split_name[-1] not in input_formats:
        format_string = ', '.join(input_formats)
        raise argparse.ArgumentTypeError(
            f'"{name}" does not have a supported file extension.\n'
            'Only the following extensions are supported:\n'
            + format_string)
    else:
        return input_formats[split_name[-1]], name


def _output_format(name):
    output_formats = {
        'spr': sprite.format.spr.save,
        'txt': sprite.format.txt.save,
        'xml': sprite.format.xml.save
    }
    split_name = name.rsplit('.', 1)
    if split_name[-1] not in output_formats:
        format_string = ', '.join(output_formats)
        raise argparse.ArgumentTypeError(
            f'"{name}" does not have a supported file extension.\n'
            'Only the following extensions are supported:\n'
            + format_string)
    else:
        return output_formats[split_name[-1]], name


def convert(input, output):
    data = input[0](input[1])
    output[0](data, output[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            'Convert between Test of Time sprite files and other formats.'),
        epilog=f"""\
--
For example:

* The following command would parse the Original game's static sprite file and
  convert it into an XML description file plus all images saved as PNG images:

{sys.argv[0]} "C:\Somewhere\Test of Time\Original\Static.spr" static.xml

* The following command would do the opposite. It would parse a static.xml file
  and using all the images it references create a new Static.spr, overwriting
  any existing file:

{sys.argv[0]} static.xml "C:\Somewhere\Test of Time\Original\Static.spr"
""")
    parser.add_argument(
        'input', type=_input_format,
        help='path to the input file, e.g. a .spr file you want to edit')
    parser.add_argument(
        'output', type=_output_format,
        help='path to the output file, e.g. a new .spr file to create')
# NOTE: With the exception of Fantasy/Unit79.spr (Worm) and invisible end
# frames, there are no .spr files that share images between multiple
# animations, unless the entire animation is the same, like in mirrored
# East/West animations.
#
# The Worm has buggy Attack animations, with a loop in the middle, so we never
# see the intended end frames, and some of the Die animations continue one
# frame too far, and then fade out what should've been the first frame of the
# next animation. Because of this, the "Die S" and "Idle N" animations share
# one frame.
#
# This means that, if I fix the broken Worm, all of ToT's sprites could be
# exported to storyboard image files without there being any frames shared
# between multiple animations.
#
# So while the sprite file format allows for this, perhaps I shouldn't try to
# make other formats support or optimize this.
#
# All current .spr files are under 1.5MB anyway. People have hundreds of GBs
# of disk space these days. They'll survive a few duplicate frames.
#
# Another NOTE: The majority of all existing animations have 12 or fewer unique
# images per animation. Only a handful have more than 20. The longest unit
# animation has 41. The longest resource animation has 20.
#
# So it should be reasonable to make the --as-storyboard flag save:
# * each unit as a single row of N/NE/E/SE/S images for the Static.spr.
# * each unit/resource animation as a single row of images.
    parser.add_argument(
        '--as-storyboard', action='store_true',
        help='instead of storing each image as a separate file')
    parser.add_argument(
        '--adjacent-mask', action='store_true',
        help='''instead of writing the mask to a separate image file, write it
                to the same file, below the image it applies to''')
    parser.add_argument(
        '--with-border', action='store_true',
        help='add a single pixel, green border around every image')
    args = parser.parse_args()

    convert(args.input, args.output)
