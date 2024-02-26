import os
import requests
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from jose import jwt, jwk


class AuthMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, jwks_url: str):
        super().__init__(app)
        self.jwks= self.get_jwks(jwks_url)


    @staticmethod
    def get_jwks(url: str) -> dict[str, str]:
        response = requests.get(url).json()
        keys = response["keys"]
        return {key["kid"]: key for key in keys}

    def decode_jwt(self, token: str):
        unverified_header = jwt.get_unverified_headers(token)
        kid = unverified_header["kid"]
        if kid not in self.jwks:
            raise HTTPException(status_code=403, detail="kid not recognized")
        jwk_data = self.jwks[kid]
        public_key = jwk.construct(jwk_data).to_pem()
        try:
            payload = jwt.decode(token, public_key, algorithms=["RS256"])
            return payload
        except:
            raise HTTPException(
                status_code=403, detail="Invalid authentication credentials"
            )
    
    async def jwt_middleware(self, request: Request, call_next):
        authorization: str = request.headers.get("Authorization")
        if authorization:
            try:
                token = authorization.split()
                user_info = self.decode_jwt(token=token)
                request.state.user = user_info
            except ValueError:
                raise HTTPException(status_code=403, detail="Invalid authorization header")
            except HTTPException as e:
                return e
        return await call_next(request)
