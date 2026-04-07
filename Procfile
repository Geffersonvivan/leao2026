web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py criar_superuser && gunicorn core.wsgi --bind 0.0.0.0:$PORT
