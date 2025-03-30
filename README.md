# PingDog
PingDog is a minimalistic console app for monitoring http services/websites availablelity.

## Instructions
1. install requirements: `pip install -r requirements.txt`
2. create a text file that contains services urls:

example:
```
https://google.com
https://github.com
```
3. run PingDog: `python PingDog.py urls.txt`
4. (optional) set calling interval using `-i`

`python PingDog.py urls.txt -i 5` : Calls services every 5 seconds
