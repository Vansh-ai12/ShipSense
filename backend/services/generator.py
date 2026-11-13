import hashlib, hmac, os, secrets


CODE_SECRET = os.environ["CODE_SECRET"]          # server secret, kept out of git

def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"     # six digits

def hash_code(code: str, order_id: str) -> str:
    return hmac.new(CODE_SECRET.encode(), f"{order_id}:{code}".encode(),
                    hashlib.sha256).hexdigest()

def verify_code(code: str, order_id: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code, order_id), stored_hash)



def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key():
    return