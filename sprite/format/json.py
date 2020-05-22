import json
import os


def save(sprite, path):
    """Save Sprite object 'sprite' to .json file 'path'"""

    img_list = sprite.save_as_pngs(os.path.splitext(path)[0])
    sprite_json = {'images': []}
    for img in img_list:
        detail = img._asdict()
        del detail['image_box']
        del detail['mask_box']
        sprite_json['images'].append(detail)
    if sprite.has_animations:
        sprite_json['frames'] = [f._asdict() for f in sprite.frames]
        sprite_json['animations'] = sprite.animation_index[:]
    with open(path, 'xt') as f:
        json.dump(sprite_json, f)
