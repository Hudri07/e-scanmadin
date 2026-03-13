from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
password = "Madin2026*"
print(pwd_context.hash(password))