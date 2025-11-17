# app/core/security.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status  # <-- 导入新工具
from fastapi.security import OAuth2PasswordBearer  # <-- 导入新工具

# --- 1. 密码哈希 ---
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# --- 2. JWT (令牌) ---
SECRET_KEY = "your-super-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 这是“守门人”的入口。它告诉 FastAPI：
# "在 /api/v1/auth/token 这个 URL 查找令牌"
# (这个 /api/v1/auth/token 是你 auth.py 里的端点)
# (注意: tokenUrl 是 *相对* 于根的路径)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- 3. 模拟数据库和认证 ---
HASHED_TEST_PASSWORD = get_password_hash("password123")
SIMULATED_USER_DB = {
    "test@example.com": {
        "hashed_password": HASHED_TEST_PASSWORD,
        "full_name": "Test User",
        "disabled": False
    }
}


def authenticate_user(username: str, password: str) -> dict | None:
    user = SIMULATED_USER_DB.get(username)
    if not user or user["disabled"]:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


# --- 4. (新增) 令牌验证器和依赖项 ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    一个 FastAPI 依赖项，用于：
    1. 从请求的 "Authorization" 标头中提取令牌。
    2. 验证令牌 (签名和过期时间)。
    3. 解码令牌并查找用户。
    4. 返回用户字典，或抛出 401 异常。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 令牌中的 "sub" (subject) 就是我们的 email/username
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        # 如果令牌无效 (签名错误, 过期等)
        raise credentials_exception

    # 从我们的模拟数据库中获取用户
    user = SIMULATED_USER_DB.get(username)
    if user is None or user["disabled"]:
        raise credentials_exception

    # 成功！返回用户字典
    return user