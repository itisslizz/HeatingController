#Heating Control System

This repository contains a smart heating control system.
It is designed to run on a RaspberryPi and requires several more 
devices to run as is: Fluksometer, HoneywellValves including motes
as well as a TMote Sky for the RaspberryPi.

It requires Python3.4 and the following libraries:
* sqlite3
* scipy
* numpy
* sklearn
* aiocoap

as well as Python2.7 including theses libraries:
* sqlite3
* web.py

## Controller System

The controller system is located in the controller directory.
To run it issue the follwing command:

'''sh
python3.4 controller.py
'''

In the controller different settings can be changed, they are at the top
of the file stored in the SETTINGS variable.
In order for it to work properly these things need to be adjusted:
* The paths for the database files in all modules
* The mac address in the building.py module

## Webserver

The webserver is the backend for the following Android App that can be
found here: https://github.com/itisslizz/RegisterAtHome

It runs on Python2.7 and requires the web.py package
Adjustment needs to be made to the path of the database file as well. Make sure
that when running the server you issue the same port as in your app.


Issue the following command to run the server and listen on port 1234
'''sh
python webserver 1234
'''

## Temperature Logger
The log_temperatures.py file contains this program. Run it using Python3.4
it accesses all the motes listed by their MAC addresses in the mac list
and logs their temperature in the database file change the MAC addresses
to the ones in your system. It is recommended it to 
issue a cronjob running the program every 15 minutes.

## Get Electricity Data
This records electricity data from a Fluksometer using its json interface. 
To run it change the url to the one of your Fluksometer in the get_electricity_data.py file.
Here a minutely cronjob should be created in order to store the electricity data.
