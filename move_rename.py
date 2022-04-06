# Finds all files recursively based on search text, moves them to specified destination folder, changes the name to random UUID to avoid files of the same name (essentially flattening a folder structure). Finally reduces files size and appends original EXIF data to image.
# Move move_rename.py to the top level directory where you would like the program to search.
# Basic usage: python move_rename.py

import os
import uuid
import exifread
from datetime import date
from PIL import Image
import piexif
import shutil

## *** Set these before you run *** ##
# Desination to copy found files to #
dest_folder = '/media/sf_ForestPreserveProject/final_360'
# Text files should start with
like_file_name = 'GSA'

# Image Shrinking #
def resize_image(image):
    file, ext = os.path.splitext(image)
    im = Image.open(image)
    exif_dict = piexif.load(im.info["exif"])
    exif_bytes = piexif.dump(exif_dict)
    # im.thumbnail((800, 800))
    im.resize((round(im.size[0]*0.5), round(im.size[1]*0.5)))
    im.save(file + '.jpg' , 'jpeg', quality=40, optimize=True, progressive=True, exif=exif_bytes)

counter = 0

# search recurively from current directory down for any files begining with "GSA"
for root, dirs, files in os.walk("."):
    for name in files:
        if(name.startswith(like_file_name)):
            # print(os.path.join(root, name))
            current_file = os.path.join(root, name)
            new_name_jpg = uuid.uuid4().hex + '.jpg'
            shutil.copy(current_file, os.path.join(dest_folder, name))
            new_file_and_path = os.path.join(dest_folder, new_name_jpg)
            os.rename(os.path.join(dest_folder, name), new_file_and_path)
            resize_image(new_file_and_path)
            counter += 1
            print('finished file : %s ' % (current_file))
            print('count: %s ' % (counter))