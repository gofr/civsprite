"""This module contains the objects used by the file format conversion modules.

Each file format conversion module should expose the following two functions:

    load(path)
        Return a Sprite object for the file at the given 'path'.
    save(sprite, path)
        Create a file at the given 'path' from the 'sprite' Sprite object.
"""

import collections
import enum
import os

from PIL import Image, ImageOps


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


Frame = collections.namedtuple('Frame', [
    'image', 'transparency',
    'start', 'loop', 'mirror', 'end', 'continuous'])
"""Object representation for an animation frame used by the Sprite object.

image - integer value in the range [0,1023], index into the images list in
        the Sprite object.
transparency - integer value in the range [0,7], 0 mean fully opaque, 7 means
               7/8 (87.5%) transparent.
start - True for an animation start frame.
loop - True for the last frame in a loop (loops back to last start).
mirror - True for frames that should be horizontally mirrored.
end - True for the last frame in an animation (this frame is not displayed)
continuous - True for all frames in a continuously repeating loop
"""


class SpriteType(enum.Enum):
    RESOURCES = 1
    STATIC = 2
    UNIT = 3


class Sprite(object):
    def __init__(self, images, frames=None, animation_index=None):
        """Create a Sprite object.

        images - list of RGBA PIL Image objects, where A is actually a 1-bit
                 channel used to represent the civilization color mask.
                 Multiple items in this list can refer to the same object.
        frames - list of Frame objects.
        animation_index - list of indexes into the 'frames' list.

        frames and animation_index are optional, since animations are
        optional in sprite files, but if one of them is non-empty, both of them
        need to be specified.
        """

        if bool(frames) != bool(animation_index):
            raise ValueError()

        self.images = images
        self.frames = frames
        self.animation_index = animation_index

        self.has_animations = bool(self.frames)

        if self.has_animations:
            if len(self.animation_index) == 32:
                self.type = SpriteType.UNIT
            else:
                self.type = SpriteType.RESOURCES
        else:
            self.type = SpriteType.STATIC

    def get_images_in_animation(self, start_frame):
        """Return list of unique images in animation starting at start_frame"""
        images = []
        for frame in self.frames[start_frame:]:
            # Exclude the end frame because it's not displayed:
            if frame.end:
                break
            # Use all() because a plain "in" does an equality check, not an
            # identity check, which would then exclude frames that look the
            # same in other animations. We now potentially save more duplicate
            # images, but hopefully cause less confusion for animation authors.
            if all(i is not self.images[frame.image] for i in images):
                images.append(self.images[frame.image])
            if frame.loop:
                break
        return images

    def find_matching_image_indexes(self, image, identical=True):
        """Return generator of indexes of images equal to 'image'

        If identity is True, return the indexes only of identical objects.
        If it is False, return the indexes of all images that look the same.
        """
        def test(img):
            return img is image if identical else img == image
        return (i for i, img in enumerate(self.images) if test(img))

    def save_as_pngs(self, images_dir, borders=True):
        """Save images in sprite as PNGs and return list of ImageDetails

        The returned list corresponds exactly to the list in self.images.
        """
        # TODO: User-friendly error-handling and possibility to override:
        os.makedirs(images_dir)

        saved_details = [None] * len(self.images)
        saved_images = []

        def save_and_update_progress(image_list, image_path, identical):
            image_details = save_images_to_file(
                image_list, image_path, borders)
            saved_images.extend(image_list)
            for n, img in enumerate(image_list):
                for idx in self.find_matching_image_indexes(img, identical):
                    saved_details[idx] = image_details[n]

        if self.has_animations:
            seen_animations = []
            for n, start_frame in enumerate(self.animation_index):
                if start_frame in seen_animations:
                    continue
                seen_animations.append(start_frame)
                # All images that have not already been saved:
                anim_images = [
                    img for img in self.get_images_in_animation(start_frame)
                    # Check identity, not just equality:
                    if all(i is not img for i in saved_images)
                ]
                if anim_images:
                    image_path = os.path.join(
                        images_dir, f'animation-{n:03d}.png')
                    save_and_update_progress(
                        anim_images, image_path, identical=True)
            unused = [
                self.images[n] for n, detail in enumerate(saved_details)
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
            static_images = list(self.images)
            directions = 5  # facing directions per unit
            unit = 0
            while static_images:
                image_path = os.path.join(images_dir, f'unit-{unit:03d}.png')
                current_images = []
                for img in static_images[0:directions]:
                    # Doing equality check here unlike for animations, because
                    # I don't expect de-duplicating equal images in static
                    # sprites will be as confusing.
                    if img not in saved_images and img not in current_images:
                        current_images.append(img)
                save_and_update_progress(
                    current_images, image_path, identical=False)
                static_images = static_images[directions:]
                unit += 1
        assert all(saved_details), "Not all images were saved"
        return saved_details


def save_images_to_file(images, path, borders=True):
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
