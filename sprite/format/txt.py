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
;   image path    = Path to the image. The path can be relative to the
;                   directory of this text file, or absolute.
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


# TODO: Move this next to the Sprite object?
class ImageDetails(collections.namedtuple('ImageDetails', [
        'image_path', 'image_x', 'image_y', 'width', 'height',
        'mask_path', 'mask_x', 'mask_y', 'image_box', 'mask_box'])):
    __slots__ = ()

    def __new__(cls, image_path, image_x, image_y, width, height,
                mask_path=None, mask_x=None, mask_y=None):
        assert os.path.isabs(image_path)
        assert (type(image_x) == type(image_y) == type(width) == type(height)
                == int)
        if mask_path is None:
            assert mask_x is None and mask_y is None
        else:
            assert os.path.isabs(mask_path)
            assert type(mask_x) == type(mask_y) == int

        # Bounding boxes for PIL (left, top, right, bottom):
        image_box = (image_x, image_y, image_x + width, image_y + height)
        mask_box = None
        if mask_path:
            mask_box = (mask_x, mask_y, mask_x + width, mask_y + height)

        return super().__new__(
            cls, image_path, image_x, image_y, width, height,
            mask_path, mask_x, mask_y, image_box, mask_box)

    def __eq__(self, other):
        return (
            self.image_path == other.image_path and
            self.image_box == other.image_box and
            self.mask_path == other.mask_path and
            self.mask_box == other.mask_box
        )

    def __hash__(self):
        return hash(tuple(self))


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


def _parse_image_details(values, root_dir):
    """Return ImageDetails object from values parsed from image text line"""
    image = {}
    try:
        image['image_path'] = os.path.abspath(
            os.path.join(root_dir, values[0]))
    except IndexError:
        raise ValueError('Image misses image path value.')
    index = 1
    for prop in ('x', 'y', 'width', 'height'):
        try:
            image[prop] = int(values[index])
            if image[prop] < 0:
                raise ValueError
        except IndexError:
            raise ValueError(f'Image misses {prop} value.')
        except ValueError:
            raise ValueError(
                f'Image has invalid {prop} value. Found "{values[index]}".'
                f' Expected integer 0 or higher.')
        index += 1
    # Turn human-readable names into object property names:
    image['image_x'] = image['x']
    image['image_y'] = image['y']
    del image['x']
    del image['y']
    try:
        mask_path = values[5]
        if mask_path == '':
            image['mask_path'] = image['image_path']
        elif mask_path:
            image['mask_path'] = os.path.abspath(
                os.path.join(root_dir, mask_path))
    except IndexError:
        pass  # This field is optional.
    index = 6
    for prop in ('x', 'y'):
        try:
            image[prop] = int(values[index])
            if image[prop] < 0:
                raise ValueError
        except IndexError:
            # The coordinates are only required if there is a mask.
            if image.get('mask_path') is not None:
                raise ValueError(f'Mask misses {prop} value.')
        except ValueError:
            raise ValueError(
                f'Mask has invalid {prop} value. Found "{values[index]}".'
                f' Expected integer 0 or higher.')
        index += 1
    # Turn human-readable names into object property names:
    if image.get('mask_path'):
        image['mask_x'] = image['x']
        image['mask_y'] = image['y']
        del image['x']
        del image['y']
    return ImageDetails(**image)


def _load_image(details):
    """Return PIL Image object from ImageDetails object"""
    source = Image.open(details.image_path)
    image = source.crop(details.image_box)
    mask = 0
    if details.mask_path is not None:
        if details.mask_path != details.image_path:
            source = Image.open(details.mask_path)
        mask = source.crop(details.mask_box).convert('L').point(
            lambda p: 255 if p else 0, '1')
    image.putalpha(mask)
    return image


def _parse_frame(values, num_images):
    """Return sprite.objects.Frame from values parsed from frame text line"""
    frame = {}
    try:
        frame['image'] = int(values[0])
        if frame['image'] < 0 or frame['image'] >= num_images:
            raise ValueError
    except IndexError:
        raise ValueError('Frame misses image index.')
    except ValueError:
        raise ValueError(
            f'Frame has invalid image index. Found "{values[0]}".'
            f' Expected integer from 0 to {num_images}.')
    try:
        frame['transparency'] = int(values[1])
        if frame['transparency'] < 0 or frame['transparency'] > 7:
            raise ValueError
    except IndexError:
        raise ValueError('Frame misses transparency value.')
    except ValueError:
        raise ValueError(
            f'Frame has invalid transparency value.'
            f' Found "{values[1]}". Expected integer from 0 to 7.')
    index = 2
    for prop in ('start', 'loop', 'mirror', 'end', 'continuous'):
        try:
            frame[prop] = bool(int(values[index]))
        except IndexError:
            raise ValueError(f'Frame misses {prop} value.')
        except ValueError:
            raise ValueError(
                f'Frame has invalid {prop} value. Found "{values[index]}".'
                ' Expected 0 or 1.')
        index += 1
    # Turn human-readable name into object property name:
    frame['end_loop'] = frame['loop']
    del frame['loop']
    return objects.Frame(**frame)


def _parse_animation(values, num_frames):
    """Return frame index from values parsed from animation text line"""
    try:
        anim_index = int(values[0])
        if anim_index < 0 or anim_index >= num_frames:
            raise ValueError
    except IndexError:
        raise ValueError(f'Animation misses frame index value.')
    except ValueError:
        raise ValueError(
            f'Animation has invalid frame index. Found "{values[0]}".'
            f' Expected an integer from 0 to {num_frames - 1}.')
    return anim_index


def load(path):
    """Load .txt file and return sprite.objects.Sprite object"""

    class Section(enum.Enum):
        IMAGES = 1
        FRAMES = 2
        ANIMATIONS = 3

    root_dir = os.path.abspath(os.path.dirname(path))

    with open(path, 'rt') as text_file:
        in_section = None
        images = []
        frames = []
        animations = []
        line_no = 0
        loaded_images = {}

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
                    values = [v.strip() for v in stripped_line.split(',')]
                    if in_section == Section.IMAGES:
                        image_details = _parse_image_details(values, root_dir)
                        if image_details in loaded_images:
                            images.append(images[loaded_images[image_details]])
                        else:
                            images.append(_load_image(image_details))
                            loaded_images[image_details] = len(images) - 1
                    elif in_section == Section.FRAMES:
                        frames.append(
                            _parse_frame(values, len(images)))
                    elif in_section == Section.ANIMATIONS:
                        animations.append(
                            _parse_animation(values, len(frames)))
            except ValueError as e:
                sys.exit(f'Error while loading {path}, line {line_no}:\n{e}')
    return objects.Sprite(images, frames, animations)


def _image_details_to_text(details, root_dir):
    image_path = os.path.relpath(details.image_path, root_dir)
    text = (
        f'{image_path},{details.image_x: >4},{details.image_y: >4}'
        f',{details.width: >4},{details.height: >4}'
    )
    if details.mask_path is not None:
        mask_path = os.path.relpath(details.mask_path, root_dir)
        if mask_path == image_path:
            mask_path = ''
        text += f', {mask_path},{details.mask_x: >4},{details.mask_y: >4}'
    return text


def _get_images_text(sprite, image_details, root_dir):
    text = IMAGES_HELP + '\n' + IMAGES_HEADER + '\n'
    titles = iter(())
    if sprite.type == objects.SpriteType.STATIC:
        # There are 5 images per unit. But use (1 + len) because it doesn't
        # matter if the titles iterator is longer than the actual number of
        # images. Don't break if someone decides they want to write a funny
        # .spr file that does not have a multiple of 5 images.
        titles = itertools.product(
            [', Unit'], range(1 + len(image_details) // 5),
            ['N', 'NE', 'E', 'SE', 'S'])
    for n in range(len(image_details)):
        details = _image_details_to_text(image_details[n], root_dir)
        text += f'{details} ; {n}{" ".join(map(str, next(titles, "")))}\n'
    return text


# TODO: Move this to the Sprite object.
def get_images_in_animation(sprite, start_frame):
    """Return list of unique images in animation starting with start_frame"""
    images = []
    for frame in sprite.frames[start_frame:]:
        # Exclude the end frame because it's not displayed:
        if frame.end:
            break
        # Use all() because a plain "in" does an equality check, not an
        # identity check, which would then exclude frames that look the same
        # in other animations. We now potentially save more duplicate images,
        # but hopefully cause less confusion for animation authors.
        if all(i is not sprite.images[frame.image] for i in images):
            images.append(sprite.images[frame.image])
        if frame.end_loop:
            break
    return images


def save_image(images, path, borders=True):
    """Save list of Image objects to path and return list of ImageDetails

    The items in the returned list correspond to the images passed in.
    """
    background = (255, 0, 255)
    border_color = (0, 255, 0)
    all_image_details = []
    if not images:
        return all_image_details
    total_width = int(borders)
    max_height = 0
    any_masks = False
    for img in images:
        total_width += img.width + int(borders)
        max_height = max(max_height, img.height)
        any_masks = any_masks or 255 in img.getdata(3)
    total_height = max_height + 2 * int(borders)
    if any_masks:
        total_height += max_height + int(borders)
    total_image = Image.new('RGB', (total_width, total_height), background)
    left = 0
    for img in images:
        current_mask = None
        if any_masks:
            current_mask = Image.new('1', img.size, None)
            current_mask.putdata(img.getdata(3))
            if borders:
                current_mask = ImageOps.expand(
                    current_mask.convert('RGB'), int(borders), border_color)
        if borders:
            current_image = ImageOps.expand(
                img, int(borders), border_color)
        else:
            current_image = img
        image_box = (left, 0, left + current_image.width, current_image.height)
        total_image.paste(current_image, image_box)
        if current_mask:
            mask_box = (
                left, int(borders) + max_height,
                left + current_mask.width,
                int(borders) + max_height + current_mask.height)
            total_image.paste(current_mask, mask_box)
        all_image_details.append(ImageDetails(
            os.path.abspath(path),
            int(borders) + left, int(borders),
            img.width, img.height,
            os.path.abspath(path) if current_mask else None,
            int(borders) + left if current_mask else None,
            2 * int(borders) + max_height if current_mask else None))
        left += img.width + int(borders)
    with open(path, 'xb') as f:
        total_image.save(f)
    return all_image_details


# TODO: Move this to the Sprite object.
def save_images(sprite, images_dir, borders=True):
    """Save PNGs for the sprite object and return list of ImageDetails

    The returned list corresponds exactly to the list in sprite.images.
    """
    # TODO: User-friendly error-handling and possibility to override:
    os.makedirs(images_dir)

    saved_details = [None] * len(sprite.images)
    saved_images = []

    def save_and_update_progress(image_list, image_path, identical):
        image_details = save_image(image_list, image_path, borders)
        saved_images.extend(image_list)
        for n, img in enumerate(image_list):
            for idx in sprite.find_matching_image_indexes(img, identical):
                saved_details[idx] = image_details[n]

    if sprite.has_animations:
        seen_animations = []
        for n, start_frame in enumerate(sprite.animation_index):
            if start_frame in seen_animations:
                continue
            seen_animations.append(start_frame)
            # All images that have not already been saved:
            anim_images = [
                img for img in get_images_in_animation(sprite, start_frame)
                # Check identity, not just equality:
                if all(i is not img for i in saved_images)
            ]
            if anim_images:
                image_path = os.path.join(images_dir, f'animation-{n:03d}.png')
                save_and_update_progress(
                    anim_images, image_path, identical=True)
        unused = [
            sprite.images[n] for n, detail in enumerate(saved_details)
            if detail is None
        ]
        row_size = 20
        for i in range(0, len(unused), row_size):
            image_path = os.path.join(
                images_dir, f'unused-{i // row_size:03d}.png')
            # This must also use identical=True, otherwise it could replace
            # the details from a used image by an unused image.
            save_and_update_progress(
                unused[i:i + row_size], image_path, identical=True)
    else:
        static_images = list(sprite.images)
        directions = 5  # facing directions per unit
        unit = 0
        while static_images:
            image_path = os.path.join(images_dir, f'unit-{unit:03d}.png')
            current_images = []
            for img in static_images[0:directions]:
                # Doing equality check here unlike for animations, because
                # I don't expect de-duplicating equal images in static sprites
                # will be as confusing.
                if img not in saved_images and img not in current_images:
                    current_images.append(img)
            save_and_update_progress(
                current_images, image_path, identical=False)
            static_images = static_images[directions:]
            unit += 1
    assert all(saved_details), "Not all images were saved"
    return saved_details


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .txt file 'path'"""

    images_dir, _ext = os.path.splitext(path)
    img_list = save_images(sprite, images_dir)
    with open(path, 'xt') as f:
        f.write(_get_images_text(sprite, img_list, os.path.dirname(path)))
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
