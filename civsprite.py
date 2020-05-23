#!/usr/bin/env python3.8

__version__ = '2.0.0'

import argparse
import sys

import sprite.format.json
import sprite.format.spr
import sprite.format.txt


def _input_format(name):
    input_formats = {
        'json': sprite.format.json.load,
        'spr': sprite.format.spr.load,
        'txt': sprite.format.txt.load
    }
    split_name = name.rsplit('.', 1)
    if split_name[-1] not in input_formats:
        format_string = ', '.join(input_formats)
        raise argparse.ArgumentTypeError(
            f'"{name}" does not have a supported file extension.\n'
            'Only the following extensions are supported:\n'
            + format_string)
    else:
        return lambda: input_formats[split_name[-1]](name)


def _output_format(name):
    output_formats = {
        'json': sprite.format.json.save,
        'spr': sprite.format.spr.save,
        'txt': sprite.format.txt.save
    }
    split_name = name.rsplit('.', 1)
    if split_name[-1] not in output_formats:
        format_string = ', '.join(output_formats)
        raise argparse.ArgumentTypeError(
            f'"{name}" does not have a supported file extension.\n'
            'Only the following extensions are supported:\n'
            + format_string)
    else:
        return lambda data: output_formats[split_name[-1]](data, name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # TODO: Don't hard-code the supported formats in here.
        # I should do the support of formats differently altogether. But unless
        # someone else starts contributing, I'm not likely to actually need
        #  anything more than what I have now either...
        description=f"""\
CivSprite {__version__}

Convert between Test of Time sprite files and other formats.

The only formats currently supported are:
* Test of Time sprite files (*.spr)
* text files with images (*.txt)
* JSON files with images (*.json)

Both the text and JSON output format produce their images in the same way.
A directory is created with the same base name as the output file with all
images created inside there using the PNG format.

Even though it only creates PNGs, other image file formats such as BMP are also
supported as input.

The generated text files look similar to Civilization II's own text files, like
Rules.txt, and contain further instructions.""",
        epilog=r"""
Examples:

Convert the Original game's static sprite file to a text file called
"static.txt" plus a directory next to it called "static" that contains PNG
images containing all the static sprites:

%(prog)s "C:\Somewhere\Test of Time\Original\Static.spr" static.txt

Convert a text file called "unit99.txt" along with all the PNG images it
references into a Test of Time sprite file:

%(prog)s unit99.txt "C:\Somewhere\Test of Time\Original\Unit99.spr"
""")
    parser.add_argument(
        'input', type=_input_format,
        help='path to the input file')
    parser.add_argument(
        'output', type=_output_format,
        help='path to the output file')
    parser.add_argument(
        '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument(
        '--debug', action='store_true',
        help='print the full stack trace(s) if something goes wrong')
    args = parser.parse_args()

    try:
        args.output(args.input())
    except Exception as e:
        if args.debug:
            raise
        else:
            message = ''
            while e:
                message += f'{e}\n  '
                e = e.__cause__ or e.__context__
            sys.exit(message)
