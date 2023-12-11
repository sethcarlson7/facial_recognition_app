import json
import boto3
import os
import uuid
import base64
import pathlib
import datatier

from configparser import ConfigParser

def lambda_handler(event, context):
  try: 
    print("**STARTING REGISTRATION**")
    print("PRINTING EVENT:\n", event)

    config_file = 'config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file

    configur = ConfigParser()
    configur.read(config_file)

    s3_profile = 's3readwrite+rekognition'
    boto3.setup_default_session(profile_name=s3_profile)

    bucketname = configur.get('s3', 'bucket_name')

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)

    print("**Accessing request body**")

    if "body" not in event:
      raise Exception("event has no body")

    body = json.loads(event["body"]) # parse the json

    if "filename" not in body:
      raise Exception("event has a body but no filename")
    if "data" not in body:
      raise Exception("event has a body but no data")

    filename = body["filename"]
    datastr = body["data"]

    print("filename:", filename)
    print("datastr (first 10 chars):", datastr[0:10])

    base64_bytes = datastr.encode()        # string -> base64 bytes
    bytes = base64.b64decode(base64_bytes) # base64 bytes -> raw bytes

    #
    # write raw bytes to local filesystem for upload:
    #
    print("**Writing local data file**")

    local_filename = "/tmp/data.pdf"

    outfile = open(local_filename, "wb")
    outfile.write(bytes)
    outfile.close()

    #
    # generate unique filename in preparation for the S3 upload:
    #
    print("**Uploading local file to S3**")

    basename = pathlib.Path(filename).stem
    extension = pathlib.Path(filename).suffix
    print("basename:", basename)
    print("extension:", extension)

    if extension != ".jpeg" and extension != "png": 
        raise Exception("expecting filename to have .jpeg or .png extension")


    print("S3 bucketkey:", filename)

    #
    # finally, upload to S3:
    #
    print("**Uploading data file to S3**")

    bucket.upload_file(local_filename, 
                       filename, 
                       ExtraArgs={
                         'ACL': 'public-read',
                         'ContentType': 'application/'+extension
                       })

    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    print("**DONE UPLOADING TO S3 REGISTRATION BUCKET**")

    s3 = boto3.client('s3')
    print("This is the bucket:", bucketname)
    object_key = filename
    print("This is the key:", object_key)

    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')

    #configure for rekognition access
    rekognition = boto3.client('rekognition', region_name='us-east-2')

    try:
      response = rekognition.index_faces(
        Image=
          {'S3Object':
            {
              'Bucket': bucketname,
              'Name': object_key
            }
          },
        CollectionId= "database-faces"
      )
      print("HERE'S THE RESPONSE: ", response)
      if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        face_id = response['FaceRecords'][0]['Face']['FaceId']
        name = object_key.split('.')[0].split('_')
        first_name = name[0]
        last_name = name[1]

        print("**Opening connection**")

        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        sql = """
          INSERT INTO 
          faces(firstname, lastname, rekognitionid)
           values(%s, %s, %s);
          """
        datatier.perform_action(dbConn, sql, [first_name, last_name, face_id])

      print("last print statement before returning")
      return {
        "statusCode": 200, 
        "body": json.dumps("Successful Registration!")
      }

    except Exception as e:
      return {
      "statusCode": 400,
      "body": json.dumps(str(e))
    }
      # print('Error processing employee image {} from bucket {}.'.format(object_key, bucketname))
      # raise e

  except Exception as err:
    print("**ERROR**")
    print(str(err))
    return {
      "statusCode": 400,
      "body": json.dumps(str(err))
    }