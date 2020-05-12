"""Module to load and save sprites as image files and a text-based description.

The text-based format is a comma-separated values format similar to what Civ2
itself uses.
"""

import enum
import collections
import itertools
import os
import sys

from PIL import Image, ImageOps

import sprite.objects as objects


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
# TODO: Move this next to the Sprite object.
ImageDetails = collections.namedtuple('ImageDetails', [
    'image_path', 'image_x', 'image_y', 'width', 'height',
    'mask_path', 'mask_x', 'mask_y'], defaults=(None, None, None))

FRAMES_HEADER = '@FRAMES'
FRAMES_HELP = f"""\
; Animation Frames
;
; An ordered list of animation frames.
;
; image, transparency, start, loop, mirror, end, continuous
;
;   image        = The image (from {IMAGES_HEADER}) to use for this frame,
;                  referenced by its index number. The first image has index 0.
;                  This can't be higher than 1023, so only a total of 1024
;                  images can be used in all animations in a single file.
;
;   transparency = A value 0 to 7, where 0 is fully opaque and 7 is 7/8
;                  transparent. Only units can have transparency.
;
;   start      = Is this frame the start of an animation? 0=no, 1=yes
;                Resource animations must start with a "start" frame.
;                Unit animations only need a "start" frame for loops.
;   loop       = Is this the end of a loop? 0=no, 1=yes. The loop jumps back to
;                the last "start" frame before it in the list.
;   mirror     = Mirror the image horizontally? 0=no, 1=yes
;   end        = Does this frame mark the end of an animation? 0=no, 1=yes
;                End frames themselves are not displayed!
;                This flag is only needed on non-looping animations.
;                If the first frame in an animation is also an end frame, that
;                turns off the animation.
;   continuous = Play this frame as part of a continuous loop? 0=no, 1=yes
;                This only applies to resources, like the Oil resources in the
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
;
; All animations must be listed here. That's:
; 8 directions x 4 actions = 32 for a unit
; 4 maps x 2 resources x 11 terrain types* = 88 for resources
; *) More terrain types are possible with ToTPP and are also supported here.
;
; If you don't need an animation for any of these, use an empty, single end
; frame animation.
;"""


def _line_to_namedtuple(line, tuple_type):
    values = [v.strip() for v in line.split(',')]
    num_fields = len(tuple_type._fields)
    min_fields = num_fields - len(tuple_type._field_defaults)
    has_defaults = min_fields < num_fields
    num_values = len(values)
    if num_values > num_fields:
        raise ValueError(
            f'Too many comma-separated values. Found {num_values} values.'
            f' Expected {"at most" if has_defaults else "only"} {num_fields}.')
    elif num_values < min_fields:
        raise ValueError(
            f'Too few comma-separated values. Found {num_values} value(s).'
            f' Expected{" at least" if has_defaults else ""} {min_fields}.')
    else:
        return tuple_type(*values)


def _parse_image(line):
    """Return a valid PIL Image object from an image text line."""
    # TODO: Turn the ImageDetails into a PIL Image object.
    return _line_to_namedtuple(line, ImageDetails)


def _parse_frame(line, num_images):
    """Return a valid sprite.objects.Frame from a frame text line."""
    frame = _line_to_namedtuple(line, objects.Frame)
    try:
        frame.image = int(frame.image)
        if frame.image < 0 or frame.image >= num_images:
            raise ValueError
    except ValueError:
        raise ValueError(
            f'Frame does not have valid image index. Found "{frame.image}".'
            f' Expected an integer from 0 to {num_images}.')
    try:
        frame.transparency = int(frame.transparency)
    except ValueError:
        raise ValueError(
            f'Frame does not have valid transparency value.'
            f' Found "{frame.transparency}". Expected an integer from 0 to 7.')
    frame.start = bool(frame.start)
    frame.end_loop = bool(frame.end_loop)
    frame.mirror = bool(frame.mirror)
    frame.end = bool(frame.end)
    frame.continuous = bool(frame.continuous)
    return frame


def _parse_animation(line, num_frames):
    """Return a valid frame index number from an animation text line."""
    try:
        anim_index = int(line)
        if anim_index < 0 or anim_index >= num_frames:
            raise ValueError
    except ValueError:
        raise ValueError(
            f'Animation does not have valid frame index. Found "{line}".'
            f' Expected an integer from 0 to {num_frames - 1}.')
    return anim_index


def load(path):
    """Load .txt file and return sprite.objects.Sprite object"""

    class Section(enum.Enum):
        IMAGES = 1
        FRAMES = 2
        ANIMATIONS = 3

    with open(path) as text_file:
        in_section = None
        images = []
        frames = []
        animations = []
        line_no = 0

        for line in text_file:
            try:
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
                            f'{FRAMES_HEADER} must come after {IMAGES_HEADER}'
                            f' and before {ANIMATIONS_HEADER}.')
                    in_section = Section.FRAMES
                elif stripped_line.upper() == ANIMATIONS_HEADER:
                    if not images or not frames:
                        raise ValueError(
                            f'{ANIMATIONS_HEADER} must come after'
                            f' {IMAGES_HEADER} and {FRAMES_HEADER}.')
                    in_section = Section.ANIMATIONS
                else:
                    if in_section == Section.IMAGES:
                        images.append(_parse_image(stripped_line))
                    elif in_section == Section.FRAMES:
                        frames.append(
                            _parse_frame(stripped_line, len(images)))
                    elif in_section == Section.ANIMATIONS:
                        animations.append(_parse_animation(
                            stripped_line, len(frames)))
            except ValueError as e:
                sys.exit(f'Error while loading {path}, line {line_no}:\n{e}')
    return objects.Sprite(images, frames, animations)


def _image_details_to_text(image_details):
    # TODO: The file paths in here can be relative or absolute.
    # Should I make sure that the paths there are always absolute?
    # Make sure the paths are relative to the text file here.
    return ', '.join(map(str, filter(lambda x: x is not None, image_details)))


def _get_images_text(sprite, image_details):
    text = IMAGES_HELP + '\n' + IMAGES_HEADER + '\n'
    titles = iter(())
    if sprite.type == objects.SpriteType.STATIC:
        # There are 5 images per unit. But use (1 + len) because it doesn't
        # matter if the titles iterator is longer than the actual number of
        # images. Don't break if someone decides they want to write a funny
        # .spr file that does not have a multiple of 5 images.
        titles = itertools.product(
            [', Unit'], range(1 + len(sprite.images) // 5),
            ['N', 'NE', 'E', 'SE', 'S'])
    for n, image in enumerate(sprite.images):
        if image_details[n]:
            details = _image_details_to_text(image_details[n])
        else:
            details = 'unused'
        text += f'{details} ; {n}{" ".join(map(str, next(titles, "")))}\n'
    return text


# TODO: Move this to the Sprite object.
def get_images_for_animation(sprite, start_frame):
    """Return list of images used in animation starting with start_frame"""
    # Create a unique list of the indexes of images used in this animation,
    # excluding the end frame which isn't displayed:
    images = []
    for frame in sprite.frames[start_frame:]:
        if frame.end:
            break
        if frame.image not in images:
            images.append(frame.image)
        if frame.end_loop:
            break
    return images


# TODO: Move this to the Sprite object.
def save_image(sprite, path, indexes, borders=True):
    """Save images marked by indexes to path and return list of ImageDetails

    The items in the returned list correspond to the indexes passed in.
    """
    all_image_details = []
    if not indexes:
        return all_image_details
    total_width = int(borders)
    max_height = 0
    any_masks = False
    for i in indexes:
        total_width += sprite.images[i].width + int(borders)
        max_height = max(max_height, sprite.images[i].height)
        any_masks = any_masks or 255 in sprite.images[i].getdata(3)
    total_height = max_height + 2 * int(borders)
    if any_masks:
        total_height += max_height + int(borders)
    total_image = Image.new('RGB', (total_width, total_height), (255, 0, 255))
    left = 0
    for n, i in enumerate(indexes):
        current_mask = None
        if any_masks:
            current_mask = Image.new('1', sprite.images[i].size, None)
            current_mask.putdata(sprite.images[i].getdata(3))
            if borders:
                current_mask = ImageOps.expand(
                    current_mask.convert('RGB'), int(borders), (0, 255, 0))
        if borders:
            current_image = ImageOps.expand(
                sprite.images[i], int(borders), (0, 255, 0))
        else:
            current_image = sprite.images[i]
        image_box = (
            left, 0,
            left + current_image.width, current_image.height)
        total_image.paste(current_image, image_box)
        if current_mask:
            mask_box = (
                left, int(borders) + max_height,
                left + current_mask.width,
                int(borders) + max_height + current_mask.height)
            total_image.paste(current_mask, mask_box)
        all_image_details.append(ImageDetails(
            path,
            int(borders) + left, int(borders),
            sprite.images[i].width, sprite.images[i].height,
            '' if current_mask else None,
            int(borders) + left if current_mask else None,
            2 * int(borders) + max_height if current_mask else None))
        left += sprite.images[i].width + int(borders)
    total_image.save(path)
    return all_image_details


# TODO: Move this to the Sprite object.
def save_images(sprite, images_dir, storyboard=True, borders=True):
    """Save PNGs for the sprite object and return list of ImageDetails

    The returned list corresponds exactly to the list in sprite.images.
    """
    # TODO: User-friendly error-handling and possibility to override:
    os.makedirs(images_dir)

    all_images = [None] * len(sprite.images)
    if storyboard:
        if sprite.has_animations:
            seen_animations = []
            for n, start_frame in enumerate(sprite.animation_index):
                if start_frame in seen_animations:
                    continue
                seen_animations.append(start_frame)
                # All images that have not already been saved:
                anim_images = [
                    i for i in get_images_for_animation(sprite, start_frame)
                    if all_images[i] is None
                ]
                if anim_images:
                    image_path = os.path.join(
                        images_dir, f'animation-{n:03d}.png')
                    image_details = save_image(
                        sprite, image_path, anim_images, borders)
                    for i, img in enumerate(anim_images):
                        all_images[img] = image_details[i]
            # TODO: What to do with all the None still in all_images? Those
            # were images that were not used in animations (or only in end
            # frames). Write them together in a leftovers file?
            # There can be quite a lot of these. E.g. 136 in Scifi/Unit46.spr.
        else:
            static_images = range(len(sprite.images))
            directions = 5  # facing directions per unit
            unit = 0
            while static_images:
                image_path = os.path.join(images_dir, f'unit-{unit:03d}.png')
                current_images = static_images[0:directions]
                image_details = save_image(
                    sprite, image_path, current_images, borders)
                for n, img in enumerate(current_images):
                    all_images[img] = image_details[n]
                static_images = static_images[directions:]
                unit += 1
    else:
        for img in sprite.images:
            # TODO: Write each image to PNG and add ImageDetails to all_images.
            pass
    return all_images


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .txt file 'path'"""

    images_dir, _ext = os.path.splitext(path)
    img_list = save_images(sprite, images_dir)
    with open(path, 'w') as f:
        f.write(_get_images_text(sprite, img_list))
        if sprite.has_animations:
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
            if sprite.type == objects.SpriteType.UNIT:
                actions = ['Attack', 'Die', 'Idle', 'Move']
                directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                titles = itertools.product(actions, directions)
            elif sprite.type == objects.SpriteType.RESOURCES:
                titles = itertools.product(
                    ['Map'], range(4),
                    ['Resource'], range(2),
                    ['Terrain'], range(len(sprite.animation_index) // 8))
            for animation in sprite.animation_index:
                if titles:
                    f.write(f'{animation: <4}')
                    f.write(f' ; {" ".join(map(str, next(titles)))}\n')
                else:
                    f.write(f'{animation}')
