
wget https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_640x360.m4v -O BigBuckBunny.mp4

kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: video-uploader
spec:
  containers:
  - name: uploader
    image: nginx:alpine  # Replace with your actual app image
    volumeMounts:
    - name: nginx-storage
      mountPath: /usr/share/nginx/html
  volumes:
  - name: nginx-storage
    persistentVolumeClaim:
      claimName: nginx-storage
EOF

kubectl cp BigBuckBunny.mp4 video-uploader:/usr/share/nginx/html/example.mp4