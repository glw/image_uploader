# image_uploader
Extract Exif GPS tags from image metadata store them in Postgresql and upload image to DigitalOcean Spaces.

example
for file in *.jpg; do python image_upload.py -i $file; done
