"""Module to load and save sprites as image files and a text-based description.

The text-based format is a comma-separated values format similar to what Civ2
itself uses.
"""

import enum
import collections
import itertools

import sprite.objects


IMAGES_HEADER = '@IMAGES'
IMAGES_HELP = """\
; Images
;
; A list of all images used by the static or animated sprites.
;
; image path, img x, img y, width, height, mask path, mask x, mask y
;
;   image path    = Path to the image, relative to directory of this text file.
;   x, y          = Top-left coordinate of the image or mask in the image file.
;   width, height = dimensions of the part of the image to use. Not repeated
;                   for the mask because it must be the same size.
;   mask path     = If the image uses a civ-specific color, the path to a
;                   black-and-white image that specifies which pixels of the
;                   above-mentioned image should be turned into the civ shade.
;                   White = turn into civ's shade. Black = Don't change.
;
; If you don't use a mask, you can leave out the mask path and its x and y
; coordinates. If the mask path is empty (whitespace only), it will use the
; same file path as that of the image.
;"""
Image = collections.namedtuple('Image', [
    'image_path', 'image_x', 'image_y', 'width', 'height',
    'mask_path', 'mask_x', 'mask_y'], defaults=(None, None, None))

FRAMES_HEADER = '@FRAMES'
FRAMES_HELP = f"""\
; Animation Frames
;
; An ordered list of animation frames.
;
; image, transparency, start, end loop, mirror, end, continuous
;
;   image        = The image (from {IMAGES_HEADER}) to use for this frame,
;                  referenced by its index number. The first image has index 0.
;
;   transparency = A value 0 to 7, where 0 is fully opaque and 7 is 7/8
;                  transparent.
;
;   start      = Is this frame the start of an animation? 0=no, 1=yes
;                Resource animations must start with a "start" frame.
;                Unit animations only need a "start" frame if they're loops.
;   end loop   = Is this the end of a loop? 0=no, 1=yes. The loop jumps back to
;                the last "start" frame before it in the frames list.
;   mirror     = Mirror the image horizontally? 0=no, 1=yes
;   end        = Does this frame mark the end of an animation? 0=no, 1=yes
;                End frames themselves are not displayed.
;   continuous = Play this frame as part of a continuous loop? 0=no, 1=yes
;                This only applies to resources, like the Oil resource in the
;                Original game. All frames in the continuously looping
;                animation should have this set to 1.
;"""

ANIMATIONS_HEADER = '@ANIMATIONS'
ANIMATIONS_HELP = f"""\
; Animations
;
; List of numeric frame IDs that mark the start of each animation. Each number
; points to a frame in the {FRAMES_HEADER} list. The first frame there has
; number 0.
;"""


def _line_to_namedtuple(line, line_no, tuple_type):
    values = [v.strip() for v in line.split(',')]
    num_fields = len(tuple_type._fields)
    min_fields = num_fields - len(tuple_type._field_defaults)
    has_defaults = min_fields < num_fields
    num_values = len(values)
    if num_values > num_fields:
        raise ValueError(
            f'Too many values on line {line_no}. Found {num_values} values.'
            f' Expected {"at most" if has_defaults else "only"} {num_fields}.')
    elif num_values < min_fields:
        raise ValueError(
            f'Too few values on line {line_no}. Found {num_values} values.'
            f' Expected{" at least" if has_defaults else ""} {min_fields}.')
    else:
        return tuple_type(*values)


def _parse_image(line, line_no):
    """Return a valid PIL Image object from an image text line."""
    # TODO: Turn the named tuple into a PIL Image object.
    return _line_to_namedtuple(line, line_no, Image)


def _parse_frame(line, line_no, num_images):
    """Return a valid sprite.objects.Frame from a frame text line."""
    frame = _line_to_namedtuple(line, line_no, sprite.objects.Frame)
    try:
        frame.image = int(frame.image)
        if frame.image < 0 or frame.image >= num_images:
            raise ValueError()
    except ValueError:
        raise ValueError(
            f'The frame on line {line_no} does not have a valid image index.'
            f' Found "{frame.image}". Expected an integer from 0 to'
            f' {num_images}.')
    try:
        frame.transparency = int(frame.transparency)
    except ValueError:
        raise ValueError(
            f'The frame on line {line_no} does not have a valid transparency'
            f' value. Found "{frame.transparency}". Expected an integer'
            ' from 0 to 7.')
    frame.start = bool(frame.start)
    frame.end_loop = bool(frame.end_loop)
    frame.mirror = bool(frame.mirror)
    frame.end = bool(frame.end)
    frame.continuous = bool(frame.continuous)
    return frame


def _parse_animation(line, line_no, num_frames):
    """Return a valid frame index number from an animation text line."""
    try:
        anim_index = int(line)
        if anim_index < 0 or anim_index >= num_frames:
            raise ValueError()
    except ValueError:
        raise ValueError(
            f'The animation on line {line_no} does not have a valid frame'
            f' index. Found "{line}". Expected an integer from 0 to'
            f' {num_frames}.')
    return anim_index


def load(path):
    """Load .txt file and return sprite.objects.Sprite object"""

    class Section(enum.Enum):
        IMAGES = 1
        FRAMES = 2
        ANIMATIONS = 3

    with open(path) as txt:
        in_section = None
        images = []
        frames = []
        animations = []
        line_no = 0

        for line in txt:
            line_no += 1
            # Strip comments and whitespace:
            stripped_line = line.split(';', 1)[0].strip()
            if not stripped_line:
                continue
            elif stripped_line.upper() == IMAGES_HEADER:
                if frames or animations:
                    raise ValueError(
                        f'{IMAGES_HEADER} must come before {FRAMES_HEADER}'
                        f' and {ANIMATIONS_HEADER}.')
                in_section = Section.IMAGES
            elif stripped_line.upper() == FRAMES_HEADER:
                if not images or animations:
                    raise ValueError(
                        f'{FRAMES_HEADER} must come after {IMAGES_HEADER} and'
                        f' before {ANIMATIONS_HEADER}.')
                in_section = Section.FRAMES
            elif stripped_line.upper() == ANIMATIONS_HEADER:
                if not images or not frames:
                    raise ValueError(
                        f'{ANIMATIONS_HEADER} must come before {IMAGES_HEADER}'
                        f' and {FRAMES_HEADER}.')
                in_section = Section.ANIMATIONS
            else:
                if in_section == Section.IMAGES:
                    images.append(_parse_image(stripped_line, line_no))
                elif in_section == Section.FRAMES:
                    frames.append(
                        _parse_frame(stripped_line, line_no, len(images)))
                elif in_section == Section.ANIMATIONS:
                    animations.append(
                        _parse_animation(stripped_line, line_no, len(frames)))
    return sprite.objects.Sprite(images, frames, animations)


def _get_images_text(images, has_animations):
    text = IMAGES_HELP + '\n' + IMAGES_HEADER + '\n'
    titles = None
    # Only Static.spr has no animations, which has 5 images per unit:
    if not has_animations:
        titles = itertools.product(
            # 1 + len() because it doesn't matter if the titles iterator is
            # longer than the actual number of images. Don't break if someone
            # decides they want to write a funny .spr file that does not have
            # a multiple of 5 images.
            ['Unit'], range(1 + len(images) // 5),
            ['N', 'NE', 'E', 'SE', 'S'])
    for n, image in enumerate(images):
        has_mask = 255 in image.getdata(3)
        # TODO: Write actual values:
        text += (
            'dummy_path.png, 0, 0, 64, 64'
            + (', dummy_mask.png, 0, 0' if has_mask else '')
            + f' ; {n}'
            + (" ".join(map(str, titles.__next__())) if titles else '')
            + '\n')
    return text


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .txt file 'path'"""
    # TODO: Save PNGs like in xml format. In same folder as .txt file.
    # TODO: Also make it possible to write multiple images to the same file,
    # so my x/y/width/height parameters in the image text format are actually
    # useful for something.
    # TODO: Load info from Rules.txt somewhere and use Unit/Terrain names from
    # that for the names of the images/animations here.
    has_animations = bool(sprite.frames)
    with open(path, 'w') as f:
        f.write(_get_images_text(sprite.images, has_animations))
        if has_animations:
            f.write('\n')
            f.write(FRAMES_HELP + '\n')
            f.write(FRAMES_HEADER + '\n')
            for n, frame in enumerate(sprite.frames):
                f.write(
                    f'{", ".join(map(lambda x: str(int(x)), frame)): <24}'
                    f' ; frame {n}\n')
            f.write('\n')
            f.write(ANIMATIONS_HELP + '\n')
            f.write(ANIMATIONS_HEADER + '\n')
            titles = None
            if len(sprite.animation_index) == 32:
                actions = ['Attack', 'Die', 'Idle', 'Move']
                directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                titles = itertools.product(actions, directions)
            elif len(sprite.animation_index) % 8 == 0:
                titles = itertools.product(
                    ['Map'], range(4),
                    ['Terrain'], range(len(sprite.animation_index) // 8),
                    ['Resource'], range(2))
            for animation in sprite.animation_index:
                if titles:
                    f.write(f'{animation: <4}')
                    f.write(f' ; {" ".join(map(str, titles.__next__()))}\n')
                else:
                    f.write(f'{animation}')
