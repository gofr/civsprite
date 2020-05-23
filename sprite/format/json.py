import json
import os

from sprite.objects import Frame, ImageDetails, Sprite


def load(path):
    with open(path, 'rt') as f:
        sprite = json.load(f)
    images = []
    for n, img in enumerate(sprite['images']):
        # Don't load the same image twice:
        first_occurrence = sprite['images'].index(img)
        if first_occurrence == n:
            images.append(ImageDetails(**img).load())
        else:
            images.append(images[first_occurrence])
    frames = sprite.get('frames')
    animations = None
    if frames:
        frames = [Frame(**f) for f in frames]
        animations = sprite['animations']
    return Sprite(images, frames, animations)


def save(sprite, path):
    """Save Sprite object 'sprite' to .json file 'path'"""

    # Open json file early, so we already own it when writing the images:
    with open(path, 'xt') as f:
        try:
            img_list = sprite.save_as_pngs(os.path.splitext(path)[0])
        except FileExistsError:
            # But if creating the image directory failed, we have no use for
            # the json file anymore either:
            f.close()
            os.remove(f.name)
            raise
        sprite_json = {'images': []}
        for img in img_list:
            detail = img._asdict()
            del detail['image_box']
            del detail['mask_box']
            sprite_json['images'].append(detail)
        if sprite.has_animations:
            sprite_json['frames'] = [f._asdict() for f in sprite.frames]
            sprite_json['animations'] = sprite.animation_index[:]
        json.dump(sprite_json, f)
