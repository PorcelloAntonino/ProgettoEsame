import email
import random
import string

import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from app.utilities.conf import settings
from app.utilities.database import get_db
from app.utilities.dependencies import get_current_user
from app.models import Dipendenti
from app.schemas.dipendente import Token, PasswordChange, DipendenteBase, RefreshTokenRequest
from app.servicies.auth import verify_password, get_password_hash, create_access_token, create_refresh_token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Questo metodo permette di effettuare il login
    """
    user = db.query(Dipendenti).filter(Dipendenti.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": Dipendenti.username})
    refresh_token = create_refresh_token(data={"sub": Dipendenti.username})  # Genera il refresh token

    # response.headers["Access-Control-Allow-Origin"] = "*"
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/token/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(request.refresh_token, settings.SECRET_KEY, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token,
            "token_type": "bearer",
            "refresh_token": request.refresh_token}


@router.get("/utenti/me", response_model=DipendenteBase)
async def read_users_me(dipendente: Dipendenti = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Questo metodo permette di ottenere i dati dell'utente attualmente autenticato
    """

    message = {
        "username": dipendente.username,
        "admin": dipendente.admin,
        "email": dipendente.email,
    }
    return message




@router.post("/utenti/me/change_password")
async def change_password(password_change: PasswordChange, db: Session = Depends(get_db),
                          current_user: Dipendenti = Depends(get_current_user)):
    """
    This method allows the currently authenticated user to change their password
    """
    db_user = db.query(Dipendenti).filter(Dipendenti.id == current_user.id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(password_change.old_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    db_user.hashed_password = get_password_hash(password_change.new_password)

    db.commit()
    db.refresh(db_user)

    return {"msg": "Password updated successfully."}


