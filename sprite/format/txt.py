"""Module to load and save sprites as image files and a text-based description.

The text-based format is a comma-separated values format similar to what Civ2
itself uses.
"""

import collections

import sprite.objects


IMAGES_HEADER = '@IMAGES'
IMAGES_HELP = """\
; Images
;
; A list of all images used by the static or animated sprites.
;
; Name, image path, img x, img y, width, height, mask path, mask x, mask y
;
;   name = Unique name to identify the image.
;   image path = Path to the image, relative to directory of this text file.
;   x, y = Top-left coordinate of the image or mask in the image file.
;   width, height = dimensions of the part of the image to use. Not repeated
;                   for the mask because that must be the same size.
;   mask path = If the image uses a civ-specific color, the path to a
;               black-and-white image that specifies which pixels of the
;               above-mentioned image should be turned into the civ shade.
;
; If you don't use a mask, you can leave out the mask path and its x and y
; coordinates. If the mask path is empty (whitespace only), it will use the
; same file path as that of the image.
;
"""
Source = collections.namedtuple('Image', [
    'name', 'image_path', 'image_x', 'image_y', 'width', 'height',
    'mask_path', 'mask_x', 'mask_y'], defaults=(None, None, None))

FRAMES_HEADER = '@FRAMES'
FRAMES_HELP = """\
; Animation Frames
;
; Image, transparency, start, end_loop, mirror, end, continuous
;
;   Image = The image (defined above) to use for this frame. You can reference
;           it either by its name or its index number (the first image is 0).
;           You can re-use the same image in multiple frames.
;   transparency = A value 0 to 7, where 0 is fully opaque and 7 is 7/8
;                  transparent.
;   start = Is this frame the start of an animation? 0=no, 1=yes
;   end_loop = Is this the end of a loop? 0=no, 1=yes. A loop loops back to the
;              last "start" frame before it in the list.
;   mirror = Mirror the image horizontally? 0=no, 1=yes
;   end = Is this frame the end of an animation? 0=no, 1=yes
;         End frames are not displayed.
;   continuous = Play this frame as part of a continuous loop? 0=no, 1=yes
;                This only applies to resources, like the Oil resource in the
;                Original game. All frames in the looping animation should have
;                this set to 1.
;
"""
Frame = collections.namedtuple('Frame', [
    'image', 'transparency',
    'start', 'end_loop', 'mirror', 'end', 'continuous'])

ANIMATIONS_HEADER = '@ANIMATIONS'
ANIMATIONS_HELP = """\
; Animations
;
; Name, index of first frame
;
;   Name = Unique name to identify the animation.
;   Index = Index into the list of frames that indicates with which frame this
;           animation starts. Counting starts at 0.
;           (You can use the same start frame multiple times if you want
;           multiple animations to look the same.)
"""
Animation = collections.namedtuple('Animation', ['name', 'frame'])


def load(path):
    """Load .txt file and return sprite.objects.Sprite object"""


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .txt file 'path'"""
    # TODO: Where should the associated PNG images be stored? In a subdirectory
    # next to the 'path'? And should the image format be configurable? E.g. to
    # save the civ color mask in alpha transparency instead of as separate
    # images, or to store images as composite storyboards somehow?
