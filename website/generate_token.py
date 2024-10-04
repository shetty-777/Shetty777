import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app

def generate_token(username, token_type, delta):
    token = jwt.encode({"username": username, "token_type": token_type, "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=delta)}, current_app.config["SECRET_KEY"], algorithm = 'HS256')
    return token