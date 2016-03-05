"""This module contains the objects used by the file format conversion modules.

Each file format conversion module should expose the following two functions:

* load(path)
  Return a Sprite object for the file at the given 'path'.
* save(sprite, path)
  Create a file at the given 'path' from the 'sprite' Sprite object.
"""

import collections


Frame = collections.namedtuple('Frame', [
    'image_index', 'transparency',
    'start', 'end_loop', 'mirror', 'end', 'continuous'])
"""Object representation for an animation frame used by the Sprite object.

image_index - integer value in the range [0,1023], index into the image_index
              list in Sprite object.
transparency - integer value in the range [0,7], 0 mean fully opaque, 7 means
               7/8 (87.5%) transparent.
start - True for an animation start frame.
end_loop - True for the last frame in a loop (loops back to last start).
mirror - True for frames that should be horizontally mirrored.
end - True for the last frame in an animation (this frame is not displayed)
continuous - True for all frames in a continuously repeating loop
"""


class Sprite(object):
    def __init__(self, images, image_index, frames=None, animation_index=None):
        """Create a Sprite object.

        images - list of RGBA PIL Image objects, where A is actually a 1-bit
                 channel used to represent the civilization color mask.
        image_index - list of indexes into the 'images' list.
        frames - list of Frame objects.
        animation_index - list of indexes into the 'frames' list.

        frames and animation_index are optional, since animations are
        optional in sprite files, but if one of them is specified, both of them
        need to be specified.
        """

        if (frames is None) != (animation_index is None):
            raise ValueError()

        self.images = images
        self.image_index = image_index
        self.frames = frames
        self.animation_index = animation_index

        self.has_animations = self.frames is not None
