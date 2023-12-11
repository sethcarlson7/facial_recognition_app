#
# Client-side python app for facial recognition app, which is calling
# a set of lambda functions in AWS through API Gateway.
# Adapted from benford app client-side. 
#

import requests
import jsons

import uuid
import pathlib
import logging
import sys
import os
import base64

from configparser import ConfigParser
import matplotlib.pyplot as plt
import matplotlib.image as img

###################################################################
#
# classes
#
class Face:

  def __init__(self, entryid, firstname, lastname, rekognitionid, bucketkey):
    self.entryid = entryid # these must match columns from DB table
    self.firstname = firstname
    self.lastname = lastname
    self.rekognitionid = rekognitionid
    self.bucketkey = bucketkey

class Attributes:

  def __init__(self, gender, agerange, emotions):
    self.gender = gender
    self.agerange = agerange
    self.emotions = emotions

############################################################
#
# prompt
#
def prompt():
  """
  Prompts the user and returns the command number

  Parameters
  ----------
  None

  Returns
  -------
  Command number entered by user (0, 1, 2, ...)
  """
  print()
  print(">> Enter a command:")
  print("   0 => end")
  print("   1 => see who's registered")
  print("   2 => register face")
  print("   3 => authenticate face")
  print("   4 => see facial attributes")
  

  cmd = input()

  if cmd == "":
    cmd = -1
  elif not cmd.isnumeric():
    cmd = -1
  else:
    cmd = int(cmd)

  return cmd

###################################################################
#
# see_registered
#
def see_registered(baseurl):
  """
  Prints out all the faces in the database

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  try:
    #
    # call the web service:
    #
    api = '/registered_faces'
    url = baseurl + api

    res = requests.get(url)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:  # we'll have an error message
        body = res.json()
        print("Error message:", body["message"])
      #
      return

    #
    # deserialize and extract users:
    #
    body = res.json()
    # print(body)
    #
    # let's map each dictionary into a User object:
    #
    faces = []
    for row in body:
      # print(row)
      face = Face(row[0], row[1], row[2], row[3], row[4])
      faces.append(face)
    #
    # Now we can think OOP:
    #
    for face in faces:
      print(face.entryid)
      print("Last Name, First Name: ", face.lastname + ",", face.firstname)
      print("Rekognition Id: " , face.rekognitionid)
      print("Bucket Key: ", face.bucketkey)

  except Exception as e:
    logging.error("see_registered() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return

############################################################
#
# register face
#
def register(baseurl):
  """
  Uploads face to S3 Registration bucket, gets RekognitionId, and updates the database

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  print("Enter facial image to register (must be jpeg or png file format)>")
  local_filename = input()

  extension = local_filename.split('.')[1]

  if extension != 'jpeg' and extension != 'png':
    print("File must be jpeg or png format")
    return

  if not pathlib.Path(local_filename).is_file():
    print("Image file '", local_filename, "' does not exist...")
    return

  print("Enter registration's first name>")
  firstname = input()

  print("Enter registration's last name>")
  lastname = input()

  try:
    #
    # build the data packet:
    #
    infile = open(local_filename, "rb")
    bytes = infile.read()
    infile.close()

    #
    # now encode the image as base64. Note b64encode returns
    # a bytes object, not a string. So then we have to convert
    # (decode) the bytes -> string, and then we can serialize
    # the string as JSON for upload to server:
    #
    data = base64.b64encode(bytes)
    datastr = data.decode()

    new_filename = firstname+"_"+lastname+"."+extension

    data = {"filename": new_filename, "data": datastr}
    #
    # call the web service:
    #
    api = '/register_faces'
    url = baseurl + api

    res = requests.put(url, json=data)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # successful registration?
    #
    body = res.json()
    print(body)
    return

  except Exception as e:
    logging.error("register() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# authenticate face
#
def authenticate(baseurl):
  """
  Uploads image to Authentication S3 bucket and returns whether their face is a match

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  print("Enter facial image to authenticate (must be jpeg or png file format)>")
  local_filename = input()

  if not pathlib.Path(local_filename).is_file():
    print("Image file '", local_filename, "' does not exist...")
    return

  extension = local_filename.split('.')[1]

  if extension != 'jpeg' and extension != 'png':
    print("File must be jpeg or png format")
    return

  try:
    #
    # build the data packet:
    #
    infile = open(local_filename, "rb")
    bytes = infile.read()
    infile.close()

    #
    # now encode the image as base64. Note b64encode returns
    # a bytes object, not a string. So then we have to convert
    # (decode) the bytes -> string, and then we can serialize
    # the string as JSON for upload to server:
    #
    data = base64.b64encode(bytes)
    datastr = data.decode()

    data = {"filename": local_filename, "data": datastr}
    #
    # call the web service:
    #
    api = '/authenticate_faces'
    url = baseurl + api

    res = requests.put(url, json=data)

    # image_to_display = img.imread(local_filename)
    # plt.imshow(image_to_display)
    # plt.show()
    
    #
    # let's look at what we got back:
    #
    if res.status_code == 403: 
      body = res.json()
      print(body)
      return
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # successful authentication?
    #
    if res.status_code == 200:
      body = res.json()
      face = body
      print("Hello, " + face[1] + " " + face[2] + "!")
      return
    else:
      print("Something else went wrong...")
      return
  
  except Exception as e:
    logging.error("authenticate() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return

###################################################################
#
# face_attributes
#
def face_attributes(baseurl):
  """
  Prints out all the attributes of a face

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  entryid = input("Enter Entry Id> ")
  
  try:
    #
    # call the web service:
    #
    api = '/face_attributes'
    url = baseurl + api

    data = {"entryid": entryid}

    res = requests.get(url, json=data)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:  # we'll have an error message
        body = res.json()
        print("Error message:", body["message"])
      #
      return

    body = res.json()
    attributes = Attributes(body['Gender'], body['AgeRange'], body['Emotions'])

    print('\nAttributes For', body['Name'])
    print("\n~Gender~\n  Prediction: ", attributes.gender['Value'])
    print("  Confidence: ", attributes.gender['Confidence'])
    print("\n~Age Range~\n  Low: ", attributes.agerange['Low'])
    print("  High: ", attributes.agerange['High'])
    print("\n~Emotions~\n  Highest Emotion: ", attributes.emotions[0]['Type'])
    print("  Confidence: ", attributes.emotions[0]['Confidence'])
    print("  Second Highest Emotion: ", attributes.emotions[1]['Type'])
    print("  Confidence: ", attributes.emotions[1]['Confidence'])
    
    return
  
  except Exception as e:
    logging.error("face_attributes() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return

############################################################
# main
#
try:
  print('** Welcome to FacialRecognitionApp **')
  print()

  # eliminate traceback so we just get error message:
  sys.tracebacklimit = 0

  #
  # what config file should we use for this session?
  #
  config_file = 'facialrecognitionapp-client-config.ini'

  print("Config file to use for this session?")
  print("Press ENTER to use default, or")
  print("enter config file name>")
  s = input()

  if s == "":  # use default
    pass  # already set
  else:
    config_file = s

  #
  # does config file exist?
  #
  if not pathlib.Path(config_file).is_file():
    print("**ERROR: config file '", config_file, "' does not exist, exiting")
    sys.exit(0)

  #
  # setup base URL to web service:
  #
  configur = ConfigParser()
  configur.read(config_file)
  baseurl = configur.get('client', 'webservice')

  #
  # make sure baseurl does not end with /, if so remove:
  #
  if len(baseurl) < 16:
    print("**ERROR: baseurl '", baseurl, "' is not nearly long enough...")
    sys.exit(0)

  if baseurl == "https://YOUR_GATEWAY_API.amazonaws.com":
    print("**ERROR: update config.ini file with your gateway endpoint")
    sys.exit(0)

  lastchar = baseurl[len(baseurl) - 1]
  if lastchar == "/":
    baseurl = baseurl[:-1]

  #
  # main processing loop:
  #
  cmd = prompt()

  while cmd != 0:
    #
    if cmd == 1:
      see_registered(baseurl)
    elif cmd == 2:
      register(baseurl)
    elif cmd == 3:
      authenticate(baseurl)
    elif cmd == 4:
      face_attributes(baseurl)
    else:
      print("** Unknown command, try again...")
    #
    cmd = prompt()

  #
  # done
  #
  print()
  print('** done **')
  sys.exit(0)

except Exception as e:
  logging.error("**ERROR: main() failed:")
  logging.error(e)
  sys.exit(0)