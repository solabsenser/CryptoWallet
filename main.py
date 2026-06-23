from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from supabase import create_client
from typing import Optional
import os
import random
import string
import hashlib
import secrets
from datetime import datetime

# ==========================================
# CONFIG
# ==========================================

APP_NAME = "WalletX"
APP_VERSION = "1.0.0"

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_KEY:
    raise Exception("SUPABASE_KEY missing")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION
)

# ==========================================
# WORDLIST
# ==========================================

WORDLIST = [
    "apple","river","future","rocket",
    "market","secure","wallet","ocean",
    "silver","energy","storm","galaxy",
    "forest","bridge","winter","crypto",
    "network","planet","vision","metal",
    "green","future","shadow","system",
    "cloud","diamond","tiger","yellow",
    "future","alpha","beta","omega",
    "dragon","sunset","thunder","matrix",
    "ghost","binary","saturn","eagle"
]

# ==========================================
# MODELS
# ==========================================

class LoginRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class CreateWalletRequest(BaseModel):
    telegram_id: int


class TransferRequest(BaseModel):
    sender_id: int
    receiver_wallet: str
    amount: float


class AdminBalanceRequest(BaseModel):
    telegram_id: int
    amount: float


# ==========================================
# HELPERS
# ==========================================

def generate_seed_phrase():

    words = []

    for _ in range(12):
        words.append(random.choice(WORDLIST))

    return " ".join(words)


def generate_wallet_address():

    alphabet = string.ascii_uppercase + string.digits

    return "UQ" + "".join(
        random.choice(alphabet)
        for _ in range(46)
    )


def generate_wallet_hash(seed):

    return hashlib.sha256(
        seed.encode()
    ).hexdigest()


def now():

    return datetime.utcnow().isoformat()


# ==========================================
# DATABASE HELPERS
# ==========================================

def get_user(telegram_id):

    result = (
        supabase
        .table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]


def get_user_by_wallet(wallet):

    result = (
        supabase
        .table("users")
        .select("*")
        .eq("wallet_address", wallet)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]


def create_user(
    telegram_id,
    username,
    first_name
):

    data = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "balance": 0,
        "wallet_created": False
    }

    (
        supabase
        .table("users")
        .insert(data)
        .execute()
    )

    return get_user(telegram_id)


def add_transaction(
    telegram_id,
    tx_type,
    amount,
    description
):

    (
        supabase
        .table("transactions")
        .insert({
            "telegram_id": telegram_id,
            "tx_type": tx_type,
            "amount": amount,
            "description": description
        })
        .execute()
    )


# ==========================================
# ROUTES
# ==========================================

@app.get("/")
async def home():

    return FileResponse(
        "index.html"
    )


@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION
    }


@app.post("/api/login")
async def login(data: LoginRequest):

    user = get_user(
        data.telegram_id
    )

    if not user:

        user = create_user(
            data.telegram_id,
            data.username,
            data.first_name
        )

    return {
        "success": True,
        "user": user
    }

# ==========================================
# CREATE WALLET
# ==========================================

@app.post("/api/create-wallet")
async def create_wallet(
    data: CreateWalletRequest
):

    user = get_user(
        data.telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.get("wallet_created"):
        return {
            "success": False,
            "message": "Wallet already exists"
        }

    seed_phrase = generate_seed_phrase()

    wallet_address = generate_wallet_address()

    wallet_hash = generate_wallet_hash(
        seed_phrase
    )

    (
        supabase
        .table("users")
        .update({
            "wallet_created": True,
            "wallet_address": wallet_address,
            "seed_phrase": seed_phrase,
            "wallet_hash": wallet_hash
        })
        .eq(
            "telegram_id",
            data.telegram_id
        )
        .execute()
    )

    add_transaction(
        data.telegram_id,
        "wallet_created",
        0,
        "Wallet created"
    )

    return {
        "success": True,
        "wallet_address": wallet_address,
        "seed_phrase": seed_phrase
    }


# ==========================================
# IMPORT WALLET
# ==========================================

@app.post("/api/import-wallet")
async def import_wallet(
    request: Request
):

    body = await request.json()

    telegram_id = body.get(
        "telegram_id"
    )

    seed_phrase = body.get(
        "seed_phrase"
    )

    if not seed_phrase:
        raise HTTPException(
            status_code=400,
            detail="Seed missing"
        )

    wallet_hash = generate_wallet_hash(
        seed_phrase
    )

    wallet_address = (
        "UQ" +
        wallet_hash[:46].upper()
    )

    (
        supabase
        .table("users")
        .update({
            "wallet_created": True,
            "wallet_address": wallet_address,
            "seed_phrase": seed_phrase,
            "wallet_hash": wallet_hash
        })
        .eq(
            "telegram_id",
            telegram_id
        )
        .execute()
    )

    add_transaction(
        telegram_id,
        "wallet_import",
        0,
        "Wallet imported"
    )

    return {
        "success": True,
        "wallet_address": wallet_address
    }


# ==========================================
# PROFILE
# ==========================================

@app.get(
    "/api/profile/{telegram_id}"
)
async def profile(
    telegram_id: int
):

    user = get_user(
        telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "success": True,
        "user": user
    }


# ==========================================
# HISTORY
# ==========================================

@app.get(
    "/api/history/{telegram_id}"
)
async def history(
    telegram_id: int
):

    history = (
        supabase
        .table("transactions")
        .select("*")
        .eq(
            "telegram_id",
            telegram_id
        )
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    return {
        "success": True,
        "transactions": history.data
    }


# ==========================================
# DASHBOARD
# ==========================================

@app.get(
    "/api/dashboard/{telegram_id}"
)
async def dashboard(
    telegram_id: int
):

    user = get_user(
        telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    tx_count = (
        supabase
        .table("transactions")
        .select(
            "*",
            count="exact"
        )
        .eq(
            "telegram_id",
            telegram_id
        )
        .execute()
    )

    return {
        "success": True,
        "balance": user.get(
            "balance",
            0
        ),
        "wallet_address": user.get(
            "wallet_address"
        ),
        "transactions": tx_count.count
    }


# ==========================================
# SEND
# ==========================================

@app.post("/api/send")
async def send(
    data: TransferRequest
):

    sender = get_user(
        data.sender_id
    )

    if not sender:
        raise HTTPException(
            status_code=404,
            detail="Sender not found"
        )

    receiver = get_user_by_wallet(
        data.receiver_wallet
    )

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    sender_balance = float(
        sender["balance"]
    )

    if sender_balance < data.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

    sender_new = (
        sender_balance -
        data.amount
    )

    receiver_new = (
        float(receiver["balance"])
        + data.amount
    )

    (
        supabase
        .table("users")
        .update({
            "balance": sender_new
        })
        .eq(
            "telegram_id",
            sender["telegram_id"]
        )
        .execute()
    )

    (
        supabase
        .table("users")
        .update({
            "balance": receiver_new
        })
        .eq(
            "telegram_id",
            receiver["telegram_id"]
        )
        .execute()
    )

    add_transaction(
        sender["telegram_id"],
        "send",
        data.amount,
        f"Sent to {receiver['wallet_address']}"
    )

    add_transaction(
        receiver["telegram_id"],
        "receive",
        data.amount,
        f"Received from {sender['wallet_address']}"
    )

    return {
        "success": True
    }

# ==========================================
# ADMIN HELPERS
# ==========================================

def is_admin(telegram_id: int):

    return telegram_id == ADMIN_ID


# ==========================================
# ADMIN STATS
# ==========================================

@app.get(
    "/api/admin/stats/{telegram_id}"
)
async def admin_stats(
    telegram_id: int
):

    if not is_admin(
        telegram_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    users = (
        supabase
        .table("users")
        .select(
            "*",
            count="exact"
        )
        .execute()
    )

    tx = (
        supabase
        .table("transactions")
        .select(
            "*",
            count="exact"
        )
        .execute()
    )

    return {
        "success": True,
        "users": users.count,
        "transactions": tx.count
    }


# ==========================================
# ADMIN USERS
# ==========================================

@app.get(
    "/api/admin/users/{telegram_id}"
)
async def admin_users(
    telegram_id: int
):

    if not is_admin(
        telegram_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    users = (
        supabase
        .table("users")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    return {
        "success": True,
        "users": users.data
    }


# ==========================================
# ADMIN ADD BALANCE
# ==========================================

@app.post(
    "/api/admin/add-balance"
)
async def admin_add_balance(
    data: AdminBalanceRequest,
    request: Request
):

    body = await request.json()

    admin_id = body.get(
        "admin_id"
    )

    if not is_admin(
        admin_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    user = get_user(
        data.telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_balance = (
        float(user["balance"])
        + data.amount
    )

    (
        supabase
        .table("users")
        .update({
            "balance": new_balance
        })
        .eq(
            "telegram_id",
            data.telegram_id
        )
        .execute()
    )

    add_transaction(
        data.telegram_id,
        "admin_credit",
        data.amount,
        "Admin balance topup"
    )

    return {
        "success": True,
        "balance": new_balance
    }


# ==========================================
# ADMIN REMOVE BALANCE
# ==========================================

@app.post(
    "/api/admin/remove-balance"
)
async def admin_remove_balance(
    data: AdminBalanceRequest,
    request: Request
):

    body = await request.json()

    admin_id = body.get(
        "admin_id"
    )

    if not is_admin(
        admin_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    user = get_user(
        data.telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    current = float(
        user["balance"]
    )

    new_balance = max(
        0,
        current - data.amount
    )

    (
        supabase
        .table("users")
        .update({
            "balance": new_balance
        })
        .eq(
            "telegram_id",
            data.telegram_id
        )
        .execute()
    )

    add_transaction(
        data.telegram_id,
        "admin_debit",
        data.amount,
        "Admin balance withdrawal"
    )

    return {
        "success": True,
        "balance": new_balance
    }


# ==========================================
# REFERRAL CODE
# ==========================================

def generate_ref_code():

    return secrets.token_hex(4).upper()


# ==========================================
# CREATE REF CODE
# ==========================================

@app.post(
    "/api/referral/create"
)
async def create_referral(
    request: Request
):

    body = await request.json()

    telegram_id = body.get(
        "telegram_id"
    )

    user = get_user(
        telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    code = generate_ref_code()

    (
        supabase
        .table("users")
        .update({
            "ref_code": code
        })
        .eq(
            "telegram_id",
            telegram_id
        )
        .execute()
    )

    return {
        "success": True,
        "code": code
    }


# ==========================================
# SECURITY
# ==========================================

@app.middleware("http")
async def security_headers(
    request,
    call_next
):

    response = await call_next(
        request
    )

    response.headers[
        "X-Frame-Options"
    ] = "DENY"

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "Referrer-Policy"
    ] = "same-origin"

    return response


# ==========================================
# VERSION
# ==========================================

@app.get("/api/version")
async def version():

    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "server_time": now()
    }
