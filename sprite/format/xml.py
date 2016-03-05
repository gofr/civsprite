import os.path
import re
import urllib.parse
import urllib.request
import xml.dom.minidom

from PIL import Image

import sprite.objects


_DOCTYPE = """<?xml version="1.0"?>
<!DOCTYPE sprites [
    <!ELEMENT sprites (source*, image*, frame*, animation*)>
    <!ELEMENT source EMPTY>
    <!ELEMENT image EMPTY>
    <!ELEMENT frame EMPTY>
    <!ELEMENT animation EMPTY>
    <!ATTLIST source
        id ID #REQUIRED
        src CDATA #REQUIRED
        mask CDATA #IMPLIED
    >
    <!ATTLIST image
        id ID #REQUIRED
        ref IDREF #REQUIRED
    >
    <!ATTLIST frame
        id ID #REQUIRED
        img CDATA #REQUIRED
        transparency NMTOKEN #IMPLIED
        start (yes|no) "yes"
        endloop (yes|no) "yes"
        mirror (yes|no) "yes"
        end (yes|no) "yes"
        continuous (yes|no) "yes"
    >
    <!ATTLIST animation
        id ID #REQUIRED
        start IDREF #REQUIRED
    >
]>"""


def _xml_id(basename, number):
    return '-'.join([basename, str(number)])


def _path_to_url(path, rect=None):
    """Return URL for a file path and optional (x, y, width, height) tuple."""

    url_path = urllib.request.pathname2url(os.path.abspath(path))
    fragment = '='.join(['xywh', ','.join(map(str, rect))]) if rect else None
    return urllib.parse.urlunsplit(('file', None, url_path, None, fragment))


def _url_to_path(url):
    """Return tuple of file path and (x, y, width, height) tuple from a URL.

    The second element of the returned tuple is None is the URL contained
    no xywh fragment.
    """

    parse_result = urllib.parse.urlsplit(url)
    path = urllib.request.url2pathname(parse_result.path)
    fragment = parse_result.fragment
    xywh = None
    if fragment:
        xywh = tuple(map(int, fragment.split('=')[1].split(',')))
    return (path, xywh)


def _xywh_coords(xywh):
    """Return (x, y, x+width, y+height) tuple from (x, y, width, height)."""

    (x, y, w, h) = xywh
    return (x, y, x + w, y + h)


def _append_animation_frame_xml(node, frame, id):
    """Append animation frame XML element to node.

    node - XML document node to append frame element to
    frame - sprite.objects.Frame object
    id - index into the list of frames in the Sprite; used to generate
         an id for the XML element.
    """

    frame_node = node.ownerDocument.createElement('frame')
    frame_node.setAttribute('id', _xml_id('frame', id))
    frame_node.setAttribute('img', _xml_id('image', frame.image_index))

    # Conditionally set attributes:
    frame.transparency and frame_node.setAttribute('transparency',
                                                   str(frame.transparency))
    frame.start and frame_node.setAttribute('start', '')
    frame.end_loop and frame_node.setAttribute('endloop', '')
    frame.mirror and frame_node.setAttribute('mirror', '')
    frame.end and frame_node.setAttribute('end', '')
    frame.continuous and frame_node.setAttribute('continuous', '')

    node.appendChild(frame_node)


def _xml_source_to_image_object(image_source_node):
    """Return an RGBA PIL Image object for a given XML <source> element.

    The alpha channel is used for the civilization color mask (0=no, 255=yes).
    """

    # TODO: Factor out image loading in such a way that multiple images from
    # the same URL but different fragments are all loaded at the same time?
    # Cache results?

    image_url = image_source_node.getAttribute('src')
    image = None
    if image_url:
        (image_path, image_xywh) = _url_to_path(image_url)
        if os.path.isfile(image_path):
            image = Image.open(image_path)
        else:
            raise ValueError('Not a valid image URL')

        if image_xywh:
            image = image.crop(_xywh_coords(image_xywh))
        if image.mode != 'RGB':
            image = image.convert('RGB')
    else:
        # Or should this be possible and generate an empty image?
        # Probably needs a warning, at least.
        raise ValueError('Image URL missing')

    mask_url = image_source_node.getAttribute('mask')
    mask = 0
    if mask_url:
        (mask_path, mask_xywh) = _url_to_path(mask_url)
        if os.path.isfile(mask_path):
            # TODO: Should probably warn if the URL doesn't resolve.
            mask = Image.open(mask_path)
            if mask_xywh:
                mask = mask.crop(_xywh_coords(mask_xywh))
                if mask.size != image.size:
                    raise ValueError('Sizes of image and mask do not match')
            if mask.mode != '1':
                mask = mask.convert('L').point(lambda x: 255 if x else 0, '1')
    image.putalpha(mask)  # Abuse alpha channel for civ color mask

    return image


def _animation_frame(frame_node, image_list):
    """Return sprite.objects.Frame object from XML elements.

    frame_node - <frame> XML element object
    image_list - list of <image> XML element objects

    Both arguments need to come from the same XML document object.
    """

    # Dereference image IDREF to get numerical image index.
    image_id = frame_node.getAttribute('img')
    image_element = frame_node.ownerDocument.getElementById(image_id)
    image_index = image_list.index(image_element)
    if image_index > 1023:
        raise ValueError()

    transparency = 0
    if frame_node.hasAttribute('transparency'):
        transparency = int(frame_node.getAttribute('transparency'))
        if transparency < 0 or transparency > 7:
            raise ValueError()

    start = frame_node.hasAttribute('start')
    end_loop = frame_node.hasAttribute('endloop')
    mirror = frame_node.hasAttribute('mirror')
    end = frame_node.hasAttribute('end')
    continuous = frame_node.hasAttribute('continuous')

    return sprite.objects.Frame(image_index, transparency,
                                start, end_loop, mirror, end, continuous)


def load(path):
    """Load .xml file and return sprite.objects.Sprite object"""

    # How smart should I try to be? E.g. I can try to parse the XML in such
    # a way as to avoid reading the same source image files multiple times,
    # or avoid writing the same image multiple times.
    # Or I can screw all that and just plain dump all the data to SPR,
    # leaving any de-duplication cleverness to the intelligence of whoever
    # wrote the XML. And avoiding reading images multiple times is probably
    # premature optimization anyway. I can do it the simple way first and
    # then see if it's all too slow or not.

    with open(path, 'r') as xml_file:
        xml_source = re.sub(r'\A.*?(?=<sprites>)', _DOCTYPE, xml_file.read(),
                            flags=re.DOTALL | re.MULTILINE)

    doc = xml.dom.minidom.parseString(xml_source)

    source_nodes = doc.getElementsByTagName('source')
    image_nodes = doc.getElementsByTagName('image')
    frame_nodes = doc.getElementsByTagName('frame')
    animation_nodes = doc.getElementsByTagName('animation')

    frames = None
    animation_index = None

    if animation_nodes:
        animation_index = [
            frame_nodes.index(doc.getElementById(a.getAttribute('start')))
            for a in animation_nodes]
        frames = [_animation_frame(f, image_nodes) for f in frame_nodes]

    images = [_xml_source_to_image_object(s) for s in source_nodes]
    image_index = [
        source_nodes.index(doc.getElementById(i.getAttribute('ref')))
        for i in image_nodes]

    return sprite.objects.Sprite(images, image_index, frames, animation_index)


def save(sprite, path):
    """Save sprite.objects.Sprite object 'sprite' to .xml file 'path'

    Also stores all the used images in individual .png files in the current
    directory.
    """

    doc = xml.dom.minidom.Document()
    root = doc.createElement('sprites')
    doc.appendChild(root)

    if sprite.image_index is not None:
        for i, image in enumerate(sprite.images):
            image_file_name = 'sprite-{}.png'.format(i)
            # XXX: Images should be stored in the same dir (or something) as
            # the xml file. Saving them in the working directory is a bug.
            image.convert('RGB').save(image_file_name)

            tag = doc.createElement('source')
            tag.setAttribute('id', _xml_id('img', i))
            tag.setAttribute('src', _path_to_url(image_file_name))

            mask_data = image.getdata(3)
            if 255 in mask_data:
                mask_file_name = 'sprite-{}-mask.png'.format(i)
                mask = Image.new('1', image.size, None)
                mask.putdata(mask_data)
                mask.save(mask_file_name)
                tag.setAttribute('mask', _path_to_url(mask_file_name))

            root.appendChild(tag)

        for i, offset in enumerate(sprite.image_index):
            tag = doc.createElement('image')
            tag.setAttribute('id', _xml_id('image', i))
            tag.setAttribute('ref', _xml_id('img', offset))
            root.appendChild(tag)

        if sprite.has_animations:
            for i, frame in enumerate(sprite.frames):
                _append_animation_frame_xml(root, frame, i)

            for i, offset in enumerate(sprite.animation_index):
                tag = doc.createElement('animation')
                tag.setAttribute('id', _xml_id('animation', i))
                tag.setAttribute('start', _xml_id('frame', offset))
                root.appendChild(tag)

    with open(path, 'w') as f:
        doc.writexml(f, addindent='    ', newl='\n')
