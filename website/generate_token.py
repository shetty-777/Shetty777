import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app


def generate_token(email_id, token_type, delta) -> str:
    token = jwt.encode(
        {
            "email_id": email_id,
            "token_type": token_type,
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=delta),
        },
        current_app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return token
