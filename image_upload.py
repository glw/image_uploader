# FPDCC image uploader for signs, utilities, benches, and other "stuff".
# Basic usage:
# python image_upload.py -i ../signs_to_be_uploaded/image.jpg

# TO DO:
## 1. resize and minimize files. Probably requires copy exif data from one file to another
## 2. tensorflow image classification for automated sign types.
## 3. add geom in SQL statement
## 4. make Try/Except smoother, so that if one step fails neither steps execute.
## 5. key board interrupt
## 6. If insert fails, change image name back to origin name.
## 7. use logging instead of print statements for debugging.


import yaml
import boto3
import uuid
import argparse
import os
import exifread
import psycopg2
import psycopg2.extras
from datetime import date

#############
## Env setup
#############
config = yaml.safe_load(open("config.yaml"))
# postgresql db
HOST = config['postgresql']['HOST']
USER = config['postgresql']['USER']
PASSWD = config['postgresql']['PASSWD']
DATABASE = config['postgresql']['DATABASE']
# D.O. spaces
REGION_NAME = config['spaces']['REGION_NAME']
ENDPOINT_URL = config['spaces']['ENDPOINT_URL']
ACCESS_KEY_ID = config['spaces']['ACCESS_KEY_ID']
SECRET_ACCESS_KEY = config['spaces']['SECRET_ACCESS_KEY']
BUCKETNAME = config['spaces']['BUCKETNAME']
SPACESPATH = config['spaces']['SPACESPATH']
SPACESDIR = config['spaces']['SPACESDIR']

###############
## Parse inputs
###############
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True, help="input image name.")
args = vars(ap.parse_args())

#######################
## file input variables
#######################
input_filename = args["input"]
file_path, file_basename = os.path.split(input_filename)

# rename file
# new_name = uuid.uuid4().hex
output_jpg = uuid.uuid4().hex + '.jpg'
# output_jpg = file_basename

# Renaming shouldnt be done locally it can simply be done when uploading to Spaces below
# os.rename(os.path.join(file_path,file_basename), os.path.join(file_path,output_jpg))

print('##################')
print('Processing File: {} ').format(input_filename)
print('##################')
print('Renaming: {} to {} ').format(file_basename, output_jpg)
print('##################')


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
            print ("Skipping file. Tag {} not present.".format(tag))
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
                    database=self.dbname,
                    user=self.dbuser,
                    password=self.dbpass
                    )
            except psycopg2.OperationalError as e:
                raise DBException("Error connecting to database on '%s'. %s" % (self.dbhost, str(e)))

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
DB = DB()

with open(input_filename, 'rb') as f:
    try:
        ###############
        ## Get metadata
        ###############
        tags = exifread.process_file(f)
        coordinates = get_coordinates(tags)
        latitude = str(coordinates[1])
        longitude = str(coordinates[0])
        current_image_date = date.today().isoformat()

        ##############################
        ## Upload metadata to postgis
        ##############################
        path = SPACESPATH
        full_path = path + output_jpg

        sql = 'insert into public.signage (name, path, full_path, latitude, longitude, current_image_date) values(%s, %s, %s, %s, %s, %s);'

        data = (output_jpg, path, full_path, latitude, longitude, current_image_date)

        #print(sql)
        #print(data)

        DB.insert_data(sql, data)

        print('Creating point at: Latitude: {}, Longitude: {} ').format(latitude, longitude)
        print('###################')

        try:
            ######################################
            print('Upload file to Digital Ocean Spaces')
            ######################################
            # s3cmd put file.jpg --acl-public s3://spacename/path/
            # s3cmd setacl s3://spacename/file.jpg --acl-public

            # https://medium.com/@tatianatylosky/uploading-files-with-python-using-digital-ocean-spaces-58c9a57eb05b
            session = boto3.session.Session()
            client = session.client('s3',
                                    region_name=REGION_NAME,
                                    endpoint_url=ENDPOINT_URL,
                                    aws_access_key_id=ACCESS_KEY_ID,
                                    aws_secret_access_key=SECRET_ACCESS_KEY)

            key_text = os.path.join(SPACESDIR, output_jpg)

            # upload file
            client.upload_file(input_filename,  # Path to local file
                                BUCKETNAME,  # Name of Space
                                os.path.join('objects', output_jpg))  # Name for remote file
            # make file public after upload
            client.put_object_acl( ACL='public-read', Bucket=BUCKETNAME, Key=key_text)

            print('##################')
            print('{} uploading complete. ').format(output_jpg)
            print('#################')

        except Exception as e:
            print('Error: Could not upload file.')
            print(e)

    except Exception as e:
        print('Error: Could not insert data.')
        print(e)

    finally:
        f.close()
