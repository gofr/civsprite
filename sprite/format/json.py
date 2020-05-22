import json
import os


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
