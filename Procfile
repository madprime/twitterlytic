web: gunicorn twitterlytic.wsgi --log-file=-
worker: celery -A twitterlytic worker --without-gossip --without-mingle --without-heartbeat
