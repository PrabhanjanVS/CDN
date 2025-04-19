To initialize the server :
hosting a container that mnts all the video directory on to port 8080 of local machine .

'''
docker run -d --name nginx-video-server -p 8080:80 `
    -v <PATH_TO_VIDEO_DIR>`
-v <PATH_TO_server_dir_nginx.conf>:/etc/nginx/conf.d/default.conf `
nginx

example:

docker run -d --name nginx-video-server -p 8080:80 -v I:\ytvideos:/usr/share/nginx/html:ro -v C:\Users\hp\Desktop\cloud\idkporj\youtubeshi\serverside\nginx.conf:/etc/nginx/conf.d/default.conf nginx
'''
Then build the app:
docker build -t flask-hls-app4:latest .

To run the app and to apply changes when changed the code here automatically into the app container.

  docker run -p 5000:5000 -v ${PWD}:/app flask-hls-app4:latest

Deploy redis:
docker run -d `
  --name redis-cache `
  -p 6379:6379 `
  -v "${PWD}\redis.conf:/usr/local/etc/redis/redis.conf" `
  redis:latest `
  redis-server /usr/local/etc/redis/redis.conf

default user name is default and password is default i think.

Story:
Server is hosted on port 8080 , redis on port 6379 and video is fetched form port 8080 to container port 8081 and to python code to store it to redis. the web is exposed on port 5000.

if using linux based add 
'''--add-host=host.docker.internal:host-gateway'''
as well in terminal.