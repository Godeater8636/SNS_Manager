from fastapi import APIRouter
from app.api.v1 import auth, users, social_accounts, posts, affiliate_links, tasks, analytics, payments

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(social_accounts.router)
api_router.include_router(posts.router)
api_router.include_router(affiliate_links.router)
api_router.include_router(tasks.router)
api_router.include_router(analytics.router)
api_router.include_router(payments.router)
