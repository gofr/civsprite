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
    parser.add_argument(
        '--with-border', action='store_true',
        help='add a single pixel, green border around every image')
    args = parser.parse_args()

    convert(args.input, args.output)
