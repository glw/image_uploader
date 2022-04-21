# Finds all files recursively based on search text, moves them to specified destination folder, 
# changes the name to random UUID to avoid files of the same name (essentially flattening a folder structure). 
# Finally reduces files size and appends original EXIF data to image.

# Move move_rename.py to the top level directory where you would like the program to search. Then update DEST_FOLDER variable.

# Basic usage: python move_rename.py

import os
import uuid
from PIL import Image
import piexif
import shutil

## *** Set these before you run *** ##
# Desination to copy found files to #
DEST_FOLDER = '/media/sf_ForestPreserveProject/final_wideangle'
# Text files should start with
LIKE_FILE_NAME = 'G0'

# Image Shrinking #
def resize_image(image):
    file, ext = os.path.splitext(image)
    im = Image.open(image)
    exif_dict = piexif.load(im.info["exif"])
    exif_bytes = piexif.dump(exif_dict)
    im.resize((round(im.size[0]*0.5), round(im.size[1]*0.5)))
    im.save(file + '.jpg' , 'jpeg', quality=40, optimize=True, progressive=True, exif=exif_bytes)

counter = 0

# search recurively from current directory down for any files begining with what you set in "LIKE_FILE_NAME"
for root, dirs, files in os.walk("."):
    for name in files:
        if(name.startswith(LIKE_FILE_NAME)):
            current_file = os.path.join(root, name)
            new_name_jpg = uuid.uuid4().hex + '.jpg'
            shutil.copy(current_file, os.path.join(DEST_FOLDER, name))
            new_file_and_path = os.path.join(DEST_FOLDER, new_name_jpg)
            os.rename(os.path.join(DEST_FOLDER, name), new_file_and_path)
            resize_image(new_file_and_path)
            counter += 1
            print('finished file : %s ' % (current_file))
            print('count: %s ' % (counter))