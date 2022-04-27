# FPDCC image uploader for signs, utilities, benches, and other "stuff".
# Basic usage:
# python image_upload.py -i ../signs_to_be_uploaded/image.jpg

# TO DO:
## DONE 1. resize and minimize files. Probably requires copy exif data from one file to another
## 2. tensorflow image classification for automated sign types.
## 3. add geom in SQL statement
## DONE 4. make Try/Except smoother, so that if one step fails neither steps execute.
## 5. key board interrupt
## DONE 6. If insert fails, change image name back to origin name.
## 7. use logging instead of print statements for debugging.
## 8. improve script so it process all images in a directory
## 9. If any part fails image goes back to original name.

# for now ignore psycopg2 warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import os
import yaml
# import boto3
# import uuid
import argparse
import exifread
import psycopg2
import psycopg2.extras
from datetime import date
# from PIL import Image
# import piexif


# Config setup
config = yaml.safe_load(open("./image_uploader/config.yaml"))
# postgresql db
HOST = config['postgresql']['HOST']
PORT = config['postgresql']['PORT']
USER = config['postgresql']['USER']
PASSWD = config['postgresql']['PASSWD']
DATABASE = config['postgresql']['DATABASE']
SCHEMA = config['postgresql']['SCHEMA']
TABLE = config['postgresql']['TABLE']
# D.O. spaces
REGION_NAME = config['spaces']['REGION_NAME']
ENDPOINT_URL = config['spaces']['ENDPOINT_URL']
ACCESS_KEY_ID = config['spaces']['ACCESS_KEY_ID']
SECRET_ACCESS_KEY = config['spaces']['SECRET_ACCESS_KEY']
BUCKETNAME = config['spaces']['BUCKETNAME']
SPACESPATH = config['spaces']['SPACESPATH']
SPACESDIR = config['spaces']['SPACESDIR']


# Parse inputs
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True, help="input image name.")
args = vars(ap.parse_args())

# file input variables
input_filename = args["input"]
file_path, file_basename = os.path.split(input_filename)

# Create new_name
# output_jpg = uuid.uuid4().hex + '.jpg'
# path_to_output_jpg = os.path.join(file_path,output_jpg)
output_jpg = file_basename
path_to_output_jpg = input_filename


# # Image Shrinking
# def resize_image(image):
#     file, ext = os.path.splitext(image)
#     im = Image.open(image)
#     exif_dict = piexif.load(im.info["exif"])
#     exif_bytes = piexif.dump(exif_dict)
#     im.resize((round(im.size[0]*0.5), round(im.size[1]*0.5)))
#     im.save(file + '.jpg' , 'jpeg', quality=40, optimize=True, progressive=True, exif=exif_bytes)

# source: https://github.com/ianare/exif-py/issues/66
def get_coordinates(tags):

    lng_ref_tag_name = "GPS GPSLongitudeRef"
    lng_tag_name = "GPS GPSLongitude"
    lat_ref_tag_name = "GPS GPSLatitudeRef"
    lat_tag_name = "GPS GPSLatitude"

    # Check if these tags are present
    gps_tags = [lng_ref_tag_name,lng_tag_name,lat_tag_name,lat_tag_name]
    for tag in gps_tags:
        if not tag in tags.keys():
            print('#################')
            print ("Skipping file. Tag %s not present." % (tag))
            print('#################')
            return None

    convert = lambda ratio: float(ratio.num)/float(ratio.den)

    lng_ref_val = tags[lng_ref_tag_name].values
    lng_coord_val = [convert(c) for c in tags[lng_tag_name].values]

    lat_ref_val = tags[lat_ref_tag_name].values
    lat_coord_val = [convert(c) for c in tags[lat_tag_name].values]

    lng_coord = sum([c/60**i for i,c in enumerate(lng_coord_val)])
    lng_coord *= (-1)**(lng_ref_val=="W")

    lat_coord = sum([c/60**i for i,c in enumerate(lat_coord_val)])
    lat_coord *= (-1)**(lat_ref_val=="S")

    return [lng_coord, lat_coord]

# source: https://gis.stackexchange.com/questions/226631/how-to-find-coordinates-from-large-csv-within-multiple-shapefile-polygons
# source: https://gis.stackexchange.com/questions/204551/insert-points-to-postgis-using-a-function
class DBException(Exception):
    pass
class DB():
    def __init__(self):
        self.conn = None
        self.dbhost = HOST
        self.dbport = PORT
        self.dbname = DATABASE
        self.dbuser = USER
        self.dbpass = PASSWD

    def _connect(self):
        """
        Connects to the database
        :return:
        """
        if self.conn is None:
            try:
                self.conn = psycopg2.connect(
                    host=self.dbhost,
                    port = self.dbport,
                    database=self.dbname,
                    user=self.dbuser,
                    password=self.dbpass
                    )
            except psycopg2.OperationalError as e:
                print('#################')
                raise DBException("Error connecting to database on '%s'. %s" % (self.dbhost, str(e)))
                print('#################')

    def _close(self):
        """
        Closes the connection to the database
        :return:
        """
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def insert_data(self, sql, data):
        """
        :param sql: text string with the sql statement
        :return:
        """
        self._connect()
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(sql, data)
        self.conn.commit()
        self._close()

    def delete_data(self, sql_remove, data_remove):
        """
         :param sql: text string with the sql statement
         :return:
        """
        self._connect()
        cur = self.conn.cursor()
        cur.execute(sql_remove, data_remove)
        self.conn.commit()
        self._close()

DB = DB()

######################
## Rename file locally
######################
print('Processing File: %s ' % (file_basename))
# print('Renaming to: %s ' % (output_jpg))
# os.rename(input_filename, path_to_output_jpg)

# Final DO Spaces location
key_text = os.path.join(SPACESDIR, output_jpg)

with open(path_to_output_jpg, 'rb') as f:
    try:
        ###############
        ## Get metadata
        ###############
        print('Get Metadata...')
        tags = exifread.process_file(f)
        coordinates = get_coordinates(tags)
        latitude = str(coordinates[1])
        longitude = str(coordinates[0])
        current_image_date = date.today().isoformat()

        #################################
        ## Shrink image keeping exif tags
        #################################
        # print('Shrinking image...')
        # resize_image(path_to_output_jpg)

        ##############################
        ## Upload metadata to postgis
        ##############################
        path = SPACESPATH
        full_path = os.path.join(SPACESPATH, key_text)
        sql = 'INSERT into ' + SCHEMA + '.' + TABLE + '(name, path, full_path, latitude, longitude, current_image_date) values(%s, %s, %s, %s, %s, %s);'
        data = (output_jpg, path, full_path, latitude, longitude, current_image_date)
        DB.insert_data(sql, data)
        print('Creating point at: Latitude: %s, Longitude: %s ' % (latitude, longitude))


        # try:
        #     ######################################
        #     # print('Upload file to Digital Ocean Spaces')
        #     ######################################

        #     # https://medium.com/@tatianatylosky/uploading-files-with-python-using-digital-ocean-spaces-58c9a57eb05b
        #     session = boto3.session.Session()
        #     client = session.client('s3',
        #                             region_name=REGION_NAME,
        #                             endpoint_url=ENDPOINT_URL,
        #                             aws_access_key_id=ACCESS_KEY_ID,
        #                             aws_secret_access_key=SECRET_ACCESS_KEY)

        #     # upload file
        #     client.upload_file(path_to_output_jpg, # Path to local file
        #                        BUCKETNAME,         # Name of Space
        #                        key_text)           # Name for remote file
            
        #     # make file public after upload
        #     client.put_object_acl( ACL='public-read', Bucket=BUCKETNAME, Key=key_text)

        #     print('%s uploading complete. \n' % (output_jpg))

        # except Exception as e:
        #     print('#################')
        #     print('Error: Could not upload file...')
        #     # If upload to Spaces did not complete then remove point from database
        #     print('Removing point from table..')
        #     sql_remove = 'DELETE from ' + SCHEMA + '.' + TABLE + ' WHERE name = %s;'
        #     data_remove = [output_jpg]
        #     DB.delete_data(sql_remove, data_remove)
        #     print(sql_remove % (output_jpg))
        #     print(e)
        #     raise
        #     print('#################')

    except Exception as e:
        print('Error: Could not insert data.')
        print(e)
        print('#################')

    finally:
        f.close()