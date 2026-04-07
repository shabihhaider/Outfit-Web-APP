"""
app/extensions.py
Flask extension singletons — initialised here, bound to the app in create_app().
Importing these from other modules avoids circular imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _rate_limit_key():
    """
    Per-user rate limiting: use JWT user ID for authenticated requests,
    fall back to IP address for unauthenticated (login, register, public).
    """
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            return f"user:{uid}"
    except Exception:
        pass
    return get_remote_address()


db       = SQLAlchemy()
migrate  = Migrate()
jwt      = JWTManager()
bcrypt   = Bcrypt()
cors     = CORS()
compress = Compress()
limiter  = Limiter(key_func=_rate_limit_key, default_limits=[])
