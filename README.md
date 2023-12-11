# facial_recognition_app

For my CS 310 - Scalable Software Architecture final project, I made a facial recognition app using the AWS Rekognition service/API. Before I could implement anything in Rekognition, I first had to make a new Collection using the CLI. This project is similar to the Project 03 Benford App in that it uses a serverless architecture with Lambda functions and API gateway. There are four basic functions on the client side:

see_registered()
This function calls a lambda function that opens the database, returning all the faces we have 
registered. Similar to users() or assets() function in project 3. 

register_face()
This function takes in an image file (I formatted it/the lambda to only allow for jpeg and png
file formats), along with the first and last name of the person we are registering. This calls a lambda function that throws this image into the database bucket with the new key format of FIRSTNAME_LASTNAME.EXT. It then calls the Rekognition service to generate a Rekognition ID unique to a face image that we’ll use later to authenticate new faces. Lastly, it enters all the information into the RDS database. 

authenticate_face()
		This function takes in an image file (same constraints as above) and calls a lambda function that uses Rekognition to see how closely the face matches to any faces we have registered in the database. If there is a close enough match, then we’ll return the name of the face given the database entry for the registered face. If it does not find a close enough match, the function will return that no match has been found. This function also uploads any images we are trying to authenticate into a separate bucket than the registration bucket (this doesn’t really add anything as the app currently is but when I architected the application I considered possibly doing something more with this bucket). 

face_attributes()
This function takes in an Entry ID from the registration database and calls a lambda function 
that finds if the ID is present in the database. If it is, we’ll find the associated image in the registration bucket and call Rekognition to deliver some attributes on the face. 

Note: Configuration Files are not included for privacy. 
