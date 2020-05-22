import io
import struct

from PIL import Image, ImageChops

import sprite.objects


FILE_HEADER_STRUCT = struct.Struct('<3l')
IMAGE_HEADER_STRUCT = struct.Struct('<16x6lBl')
IMAGE_ROW_HEADER_STRUCT = struct.Struct('<2l')


def _rgbm_to_int(rgbm):
    """Return 16-bit color unsigned short integer from (R,G,B,mask) tuple."""

    (r, g, b, mask) = rgbm
    return bool(mask) << 15 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)


def _int_to_rgbm(color):
    """Return (R,G,B,mask) tuple from 16-bit color unsigned short integer."""

    rgbm = [
        (c << 3) + (c >> 2)
        for c in [(color >> 10) & 31, (color >> 5) & 31, color & 31]
    ]
    rgbm.append((color >> 15) * 255)
    return tuple(rgbm)


def _read_spr_image(spr_file):
    """Return PIL Image for image at current location in spr_file object."""

    (width, height, left, top, right, bottom, bgcolor, size) = \
        IMAGE_HEADER_STRUCT.unpack(spr_file.read(IMAGE_HEADER_STRUCT.size))

    # Turn bits CCCCCBGR (with Cs the 5-bit color channel value) into RGBm.
    # Use _int_to_rgbm() to get consistent 16-bit to 24-bit color conversion.
    bgchannel = bgcolor >> 3
    bgcolor = _int_to_rgbm(
        (((bgcolor & 1) * bgchannel) << 10) +  # R
        (((bgcolor & 2) * bgchannel) << 4) +  # G
        (((bgcolor & 4) * bgchannel) >> 2))  # B

    # empty lines above bounding box
    image_data = [bgcolor] * width * top

    while size > 10:
        (empty_bytes, row_bytes) = IMAGE_ROW_HEADER_STRUCT.unpack(
            spr_file.read(IMAGE_ROW_HEADER_STRUCT.size))
        size -= IMAGE_ROW_HEADER_STRUCT.size

        if empty_bytes:
            image_data.extend([bgcolor] * (empty_bytes // 2))
        if row_bytes:
            image_data.extend(
                map(_int_to_rgbm,
                    struct.unpack(
                        '<{}H'.format(row_bytes // 2),
                        spr_file.read(row_bytes))))
            size -= row_bytes

        # empty pixels at end of line
        image_data.extend([bgcolor] * (width - (empty_bytes + row_bytes) // 2))

    # empty lines below bounding box
    image_data.extend([bgcolor] * width * (height - bottom))

    # Skip over the trailing 10 null bytes:
    spr_file.seek(10, io.SEEK_CUR)

    image = Image.new('RGBA', (width, height), None)
    image.putdata(image_data)

    return image


def _image_object_to_sprite_image(image):
    """Return binary SPR representation of an RGBA PIL Image object.

    The alpha channel is used for the civilization color mask (0=no, 255=yes).
    """

    transparent = (255, 0, 255, 0)  # magenta without color mask
    blank_image = Image.new('RGB', image.size, transparent)
    bounding_box = \
        ImageChops.difference(image.convert('RGB'), blank_image).getbbox()
    (bbox_left, bbox_top, bbox_right, bbox_bottom) = \
        bounding_box or (0, 0, 0, 0)
    image_data = b''

    if bounding_box is not None:
        bbox_data = list(image.crop(bounding_box).getdata())
        bbox_width = bbox_right - bbox_left

        for n in range(0, len(bbox_data), bbox_width):
            row = bbox_data[n:n + bbox_width]
            # Skip leading transparent pixels
            first_pixel = 0
            while first_pixel < bbox_width and row[first_pixel] == transparent:
                first_pixel += 1

            empty_bytes = 0
            row_data = []
            if first_pixel != bbox_width:
                # Skip trailing transparent pixels
                last_pixel = bbox_width - 1
                while (last_pixel > first_pixel and
                        row[last_pixel] == transparent):
                    last_pixel -= 1
                empty_bytes = bbox_left + first_pixel
                row_data = [
                    _rgbm_to_int(p) for p in row[first_pixel:last_pixel + 1]
                ]

            image_data += IMAGE_ROW_HEADER_STRUCT.pack(
                empty_bytes * 2, len(row_data) * 2
            ) + struct.pack('<{}H'.format(len(row_data)), *row_data)

    return IMAGE_HEADER_STRUCT.pack(
        image.width, image.height,
        bbox_left, bbox_top, bbox_right, bbox_bottom,
        0xFD, len(image_data) + 10) + image_data + (b'\0' * 10)


def _int_to_frame(frame):
    """Return a sprite.objects.Frame object for an integer frame value."""

    image = frame & 1023
    transparency = (frame >> 10) & 7
    start = bool((frame >> 13) & 1)
    loop = bool((frame >> 14) & 1)
    mirror = bool((frame >> 15) & 1)
    end = bool((frame >> 24) & 1)
    continuous = bool((frame >> 25) & 1)

    return sprite.objects.Frame(
        image, transparency, start, loop, mirror, end, continuous)


def _frame_to_int(frame):
    """Return an integer frame value for a sprite.objects.Frame object."""

    return ((frame.image & 1023) | ((frame.transparency & 7) << 10) |
            (frame.start << 13) | (frame.loop << 14) |
            (frame.mirror << 15) | (0x06 << 16) | (frame.end << 24) |
            (frame.continuous << 25))


def load(path):
    """Load .spr file and return sprite.objects.Sprite object"""

    # TODO: Add error handling
    with open(path, 'rb') as spr_file:
        header_struct = FILE_HEADER_STRUCT
        (animation_offset, image_index_offset, images_offset) = \
            header_struct.unpack(spr_file.read(header_struct.size))

        frames = None
        animation_index = None
        if animation_offset:
            anim_size = image_index_offset - animation_offset
            spr_file.seek(animation_offset)
            anim_data = list(struct.unpack('<{}l'.format(anim_size // 4),
                                           spr_file.read(anim_size)))
            first_frame = anim_data[0]
            for index, value in enumerate(anim_data):
                if (index * 4) + animation_offset == first_frame:
                    animation_index = anim_data[0:index]
                    frames = list(map(_int_to_frame, anim_data[index:]))
                    break
                elif value < first_frame:
                    first_frame = value

            # turn file offsets into list indexes
            animation_index = [(i - first_frame) // 4 for i in animation_index]

        image_index_size = images_offset - image_index_offset
        spr_file.seek(image_index_offset)
        image_index = list(struct.unpack('<{}l'.format(image_index_size // 4),
                                         spr_file.read(image_index_size)))

        image_sources = []
        image_offset_map = {}
        while True:
            image_offset = spr_file.tell() - images_offset
            if image_offset == image_index[-1]:  # final index points to EOF
                image_index.pop()
                break
            image_offset_map[image_offset] = len(image_sources)
            image_sources.append(_read_spr_image(spr_file))

    # This is normally a no-op, but not e.g. for SpriteGen-generated spr files
    # where the index refers to each image 5 times:
    images = [image_sources[image_offset_map[x]] for x in image_index]
    return sprite.objects.Sprite(images, frames, animation_index)


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .spr file 'path'"""

    header_struct = FILE_HEADER_STRUCT
    if sprite.has_animations:
        animations_offset = header_struct.size
        image_index_offset = (
            header_struct.size +
            4 * (len(sprite.animation_index) + len(sprite.frames)))
    else:
        animations_offset = 0
        image_index_offset = header_struct.size

    first_image_offset = image_index_offset + 4 * (len(sprite.images) + 1)

    with open(path, 'xb') as spr_file:
        spr_file.write(header_struct.pack(
            animations_offset, image_index_offset, first_image_offset))

        if sprite.has_animations:
            animation_data = [
                animations_offset + 4 * len(sprite.animation_index) + 4 * i
                for i in sprite.animation_index]
            animation_data.extend(map(_frame_to_int, sprite.frames))
            spr_file.write(
                struct.pack('<{}l'.format(len(animation_data)),
                            *animation_data))

        assert image_index_offset == spr_file.tell()
        # Skip past image index for now:
        spr_file.seek(first_image_offset)

        image_index = []
        current_end = 0
        for n, img in enumerate(sprite.images):
            first_occurrence = next(sprite.find_matching_image_indexes(img))
            if first_occurrence == n:
                image_data = _image_object_to_sprite_image(img)
                image_index.append(current_end)
                spr_file.write(image_data)
                current_end += len(image_data)
            else:
                # We've already written this image. Just add the same offset
                # to the index again.
                image_index.append(image_index[first_occurrence])
        image_index.append(current_end)  # EOF

        # Go back and write the image index:
        spr_file.seek(image_index_offset)
        spr_file.write(struct.pack('<{}l'.format(len(image_index)),
                                   *image_index))
