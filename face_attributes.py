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

    if "entryid" not in body:
      raise Exception("event has a body but no entryid")

    entryid = body["entryid"]

    print("entryid: ", entryid)

    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')

    print("**Opening connection**")

    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

    sql = """
        SELECT * FROM faces WHERE entryid = %s
    """

    desired_face = datatier.retrieve_one_row(dbConn, sql, [entryid])

    if desired_face:
        s3 = boto3.client('s3')
        image_bytes = s3.get_object(Bucket=bucketname, Key=desired_face[4])['Body'].read()
        rekognition = boto3.client('rekognition', region_name='us-east-2')

        response = rekognition.detect_faces(
            Image= { 
                'S3Object':
                {
                  'Bucket': bucketname,
                  'Name': desired_face[4]
                }
            },
                Attributes=["ALL"]
        )

        print(response)

        return {
            "statusCode": 200, 
            "body": json.dumps({
              "Gender": response["FaceDetails"][0]["Gender"],
              "AgeRange": response["FaceDetails"][0]["AgeRange"],
              "Emotions": response["FaceDetails"][0]["Emotions"], 
              "Name": desired_face[1] + " " + desired_face[2]
              })
        }

    else: 
        return {
            "statusCode": 403, 
            "body": json.dumps("Entry does not exist!")
          }

  except Exception as err:
    print("**ERROR**")
    print(str(err))
    return {
      "statusCode": 400,
      "body": json.dumps(str(err))
    }