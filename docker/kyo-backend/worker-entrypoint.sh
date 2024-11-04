#!/bin/sh

until cd /app/kyo-project
do
    echo "Waiting for server volume..."
done

export CLOUDINARY_URL=$(cat /run/secrets/CLOUDINARY_URL)
export S3_ACCESS=$(cat /run/secrets/S3_ACCESS)
export S3_SECRET=$(cat /run/secrets/S3_SECRET)

python manage.py rqworker default