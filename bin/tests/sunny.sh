AUTH_USER=$(grep "TEST_USER=" secrets.py | cut -f2 -d"'")
AUTH_PASS=$(grep "TEST_PASSWORD=" secrets.py | cut -f2 -d"'")
AUTH_PARAM="--auth ${AUTH_USER}:${AUTH_PASS} --auth-type basic"
#REDIRECT="--follow"
#PRINT="--print hbHB"
#DEBUG="--debug"

PARAMS="${PRINT} ${AUTH_PARAM} ${REDIRECT} ${DEBUG}"

# GET
http ${PARAMS} http://localhost:5000/api/v1.0/users/
http ${PARAMS} http://localhost:5000/api/v1.0/users/1
http ${PARAMS} http://localhost:5000/api/v1.0/users/3/publications/1/subscriptions/
http ${PARAMS} http://localhost:5000/api/v1.0/users/3/publications/1/messages/
http ${PARAMS} http://localhost:5000/api/v1.0/users/2/devices/2/messages/
# CREATE
http POST http://localhost:5000/api/v1.0/users/ name='Administrator' description='Administrator' email=admin@localhost.com username=admin password=1234
http ${PARAMS} POST http://localhost:5000/api/v1.0/users/ name=buster description='Buster' email=buster@localhost.com username=admin password=1234
# PUT
http ${PARAMS} PUT http://localhost:5000/api/v1.0/users/7 name=lenny description='Lenny' email=lenny@localhost.com username=admin password=1234
# PATCH
http ${PARAMS} PATCH http://localhost:5000/api/v1.0/users/7 name=buster description='Buster' email=buster@localhost.com
http ${PARAMS} PATCH http://localhost:5000/api/v1.0/users/7 description=a
http ${PARAMS} PATCH http://localhost:5000/api/v1.0/users/6 name=lenny description='Lenny' email=lenny@localhost.com
# DELETE
http ${PARAMS} DELETE http://localhost:5000/api/v1.0/users/6
http ${PARAMS} DELETE http://localhost:5000/api/v1.0/users/