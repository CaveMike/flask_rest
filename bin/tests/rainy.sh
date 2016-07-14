AUTH_USER="admin"
AUTH_PASS="1234"
AUTH_PARAM="--auth ${AUTH_USER}:${AUTH_PASS} --auth-type basic"
REDIRECT="--follow"
#PRINT="--print hbHB"
#DEBUG="--debug"

PARAMS="${PRINT} ${AUTH_PARAM} ${REDIRECT} ${DEBUG}"

# GET
# CREATE
http ${PARAMS} POST http://localhost:5000/api/v1.0/users/ name=buster
# PUT
http ${PARAMS} PUT http://localhost:5000/api/v1.0/users/7 description=fuzzy
# PATCH
# DELETE