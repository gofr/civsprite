"""Module to load and save sprites as image files and a text-based description.

The text-based format is a comma-separated values format similar to what Civ2
itself uses.
"""

import sprite.objects


SOURCES_HEADER = '@SOURCES'
SOURCES_HELP = """\
; Image sources
;
; A list of all images used by the static or animated sprites. They can be
; referenced by number in later sections. The first image is number 0.
;
; Image file path, img x, img y, width, height, mask file path, mask x, mask y
;
;   image file path = Image file path relative to the directory this text file
;                     is in.
;   x, y = Top-left coordinate of the image or mask in the image file.
;   width, height = dimensions of the part of the image to use. Not repeated
;                   for the mask because that must be the same size.
;   mask file path = If the image uses a civ-specific color, the path to a
;                    black-and-white image that specifies which pixels of the
;                    above-mentioned image should be turned into the civ shade.
;
; If you don't use a mask, you can leave out the mask file path and its x and y
; coordinates. If the mask path is empty (whitespace only), it will use the
; same file path as that of the image.
;
"""

IMAGES_HEADER = '@IMAGES'
IMAGES_HELP = """\
; Images
;
; Name, image source number
;
;   Name = Arbitrary name meant primarily for humans to identify the image.
;          Mainly useful to name the static sprites.
;   Image source number = Index into the list of image sources. The first image
;                         source in that list has index 0.
;
"""
# TODO: Isn't the whole @IMAGES section only useful for Static.spr files?
# Should I use this section only for non-animated sprites? If the sprites are
# animated, reference @SOURCES directly in @FRAMES?
# Would this cause any problems exporting any of ToT's existing .spr files?

FRAMES_HEADER = '@FRAMES'
FRAMES_HELP = """\
; Animation Frames
;
; Image name, transparency, start, end_loop, mirror, end, continuous
;
;   Image name = The image to use for this frame, using the name from the
;                Images section.
;                (You can re-use the same image in multiple frames.)
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

ANIMATIONS_HEADER = '@ANIMATIONS'
ANIMATIONS_HELP = """\
; Animations
;
; Name, index of first frame
;
;   Name = Arbitrary name meant for humans to identify the animation.
;   Index = Index into the list of frames that indicates with which frame this
;           animation starts. Counting starts at 0.
;           (You can use the same start frame multiple times if you want
;           multiple animations to look the same.)
"""


def load(path):
    """Load .txt file and return sprite.objects.Sprite object"""


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .txt file 'path'"""
    # TODO: Where should the associated PNG images be stored? In a subdirectory
    # next to the 'path'? And should the image format be configurable? E.g. to
    # save the civ color mask in alpha transparency instead of as separate
    # images, or to store images as composite storyboards somehow?
