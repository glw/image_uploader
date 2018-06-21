# FPDCC image uploader for signs and utilities.
import yaml
import boto3
import uuid
#import PIL
#import csvkit
import argparse
import os
import exifread
import psycopg2
import psycopg2.extras
#from exif_read import ExifRead
#from geo import normalize_bearing, interpolate_lat_lon, gps_distance

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
#new_name = uuid.uuid4().hex
#output_jpg = new_name + '.jpg'
output_jpg = file_basename
#os.rename(os.path.join(file_path,file_basename), os.path.join(file_path,output_jpg))


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
    def __init__(self, parent_widget):
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

    def insert_data(self, sql):
        """
        :param sql: text string with the sql statement
        :return:
        """
        self._connect()
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        #print(sql)
        cur.execute(sql)
        self.conn.commit()
        self._close()

with open(os.path.join(file_path,output_jpg), 'rb') as f:
    try:
        ###############
        ## Get metadata
        ###############
        tags = exifread.process_file(f)
        coordinates = get_coordinates(tags)
        latitude = coordinates[1]
        longitude =coordinates[0]


        ##############################
        ## Upload metadata to postgis
        ##############################

        path = SPACESPATH
        fullpath = SPACESPATH + '/' + output_jpg
        sql = 'insert into public.signage (name, path, fullpath, latitude, longitude, geom) values(%s, %s, %s, %s, %s, ST_MakePoint(%s, %s), 4326));', (output_jpg, path, fullpath, latitude, longitude, longitude, latitude)
        DB = DB()
        DB.insert_data(sql)



        ######################################
        ## Upload file to Digital Ocean Spaces
        ######################################
        # s3cmd put file.jpg --acl-public s3://spacename/path/
        # s3cmd setacl s3://spacename/file.jpg --acl-public

        # https://medium.com/@tatianatylosky/uploading-files-with-python-using-digital-ocean-spaces-58c9a57eb05b
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name=REGION_NAME,
                                endpoint_url=ENDPOINT_URL,
                                aws_access_key_id=AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        # upload file
        client.upload_file('/path/to/file.jpg',  # Path to local file
                            BUCKETNAME,  # Name of Space
                            'remote_file.jpg')  # Name for remote file
        # make file public after upload
        client.put_object_acl( ACL='public-read', Bucket=BUCKETNAME, Key=KEYNAME )

    finally:
        f.close()
