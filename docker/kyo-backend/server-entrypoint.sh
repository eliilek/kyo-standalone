#!/bin/sh

until cd /app/kyo-project
do
	echo "Waiting for server volume..."
done

until python manage.py makemigrations
do
	echo "Waiting for last-minute migrations to process..."
done

until python manage.py migrate
do
	echo "Waiting for db to be ready..."
	sleep 2
done

python manage.py collectstatic --noinput

export CLOUDINARY_URL=$(cat /run/secrets/CLOUDINARY_URL)
export S3_ACCESS=$(cat /run/secrets/S3_ACCESS)
export S3_SECRET=$(cat /run/secrets/S3_SECRET)

daphne -b 0.0.0.0 -p 8000 project.asgi:application