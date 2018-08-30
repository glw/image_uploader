# image_uploader
Extract Exif GPS tags from image metadata store them in Postgresql and upload image to DigitalOcean Spaces


Right now this uses docker for a current version of gdal, because of the easy way to now transfer exif tags with gdal_translate.