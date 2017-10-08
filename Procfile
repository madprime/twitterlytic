web: gunicorn twitterlytic.wsgi --log-file=-
worker: celery -A twitterlytic worker -l info --without-gossip --without-mingle --without-heartbeat
