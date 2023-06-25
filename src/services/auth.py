from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.repository import users as repo_users


class Auth:
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    SECRET_KEY = 'secret'
    ALGORITHM = 'HS256'
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/auth/login')
    
    def verify_password(self, plain_password: str, hashed_password: str):
        result = self.pwd_context.verify(plain_password, hashed_password)
        return result
    
    def get_password_hash(self, password: str):
        result = self.pwd_context.hash(password)
        return result
    
    async def create_access_token(self, data: dict, expires: Optional[float] = None):
        payload = data.copy()
        if expires:
            expires_time = datetime.utcnow() + timedelta(seconds=expires)
        else:
            expires_time = datetime.utcnow() + timedelta(minutes=15)
        payload.update({'iat': datetime.utcnow(), 'exp': expires_time, 'scope': 'access_token'})
        access_token = jwt.encode(payload, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return access_token
    
    async def create_refresh_token(self, data: dict, expires: Optional[float] = None):
        payload = data.copy()
        if expires:
            expires_time = datetime.utcnow() + timedelta(seconds=expires)
        else:
            expires_time = datetime.utcnow() + timedelta(minutes=15)
        payload.update({'iat': datetime.utcnow(), 'exp': expires_time, 'scope': 'refresh_token'})
        access_token = jwt.encode(payload, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return access_token
    
    async def decode_refresh_token(self, refresh_token: str):
        try:
            payload = jwt.decode(refresh_token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload['scope'] == 'refresh_token':
                email = payload['sub']
                return email
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid scope for token')
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)): # aka decode_access_token
        credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                              detail="Couldn't validate credentials",
                                              headers={'WWW-Authenticate': 'Bearer'})
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload['scope'] == 'access_token':
                email = payload['sub']
                if not email:
                    raise credentials_exception
            else:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        user = await repo_users.get_user_by_email(email, db)
        if not user:
            raise credentials_exception
        return user


auth_service = Auth()