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
        description=(
            'Convert between Test of Time sprite files and other formats.'),
        epilog=f"""\
--
For example:

* The following command would parse the Original game's static sprite file and
  convert it into a text description file plus all images saved as PNG images:

%(prog)s "C:\Somewhere\Test of Time\Original\Static.spr" static.txt

* The following command would do the opposite. It would parse a static.txt file
  and using all the images it references create a new Static.spr:

%(prog)s static.txt "C:\Somewhere\Test of Time\Original\Static.spr"
""")
    parser.add_argument(
        'input', type=_input_format,
        help='path to the input file, e.g. a .spr file you want to edit')
    parser.add_argument(
        'output', type=_output_format,
        help='path to the output file, e.g. a new .spr file to create')
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
