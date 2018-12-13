# Image Uploader
Extract Exif GPS tags from image metadata store them in Postgresql and upload image to DigitalOcean Spaces. (Probably only works on JPG)

1. Clone the repository

2. Create a python 3 virtual environment
```
mkvirtualenv image_upload
```
3. Install required python libraries
```
cd image_uploader
pip install requirements.txt
```
4. Run
```
for file in *.jpg; do python image_upload.py -i $file; done
```
