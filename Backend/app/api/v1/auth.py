# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.models.file import Token
from app.core.security import authenticate_user, create_access_token

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
        # OAuth2PasswordRequestForm 会自动从表单中
        # 提取 "username" 和 "password"
        form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    处理登录表单，返回一个 access token
    """
    # form_data.username 对应你前端的 "email" 字段
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="不正确的用户名或密码",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 用户名/密码正确，为他们创建一个令牌
    # 令牌中存储的数据是 "sub" (subject), 即用户的 email
    access_token = create_access_token(
        data={"sub": form_data.username}
    )

    return {"access_token": access_token, "token_type": "bearer"}