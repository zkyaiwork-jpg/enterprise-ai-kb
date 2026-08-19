from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import configure_logging
from app.database.init_db import init_db

configure_logging()
init_db()

from app.api import document
from app.api import search
from app.api import chat
from app.api import manage
from app.api import stats
from app.api import health
from app.api import folders
from app.api import audit
from app.api import users
from app.api import departments
from app.api import teams
from app.api import model_config
from app.routers import auth
from app.services import reranker_service


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        reranker_service.load_reranker()
        reranker_service.warmup_reranker()
        logger.info("Reranker ready")
    except Exception as exc:
        reranker_service.mark_reranker_unavailable(exc)
        logger.error(
            "Reranker unavailable fallback=chroma_order error_type=%s",
            type(exc).__name__,
        )
    yield

app = FastAPI(
    title = "企业AI知识库助手",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^http://(?:localhost|127\.0\.0\.1)(?::\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(manage.router)

app.include_router(chat.router)

app.include_router(document.router)

app.include_router(search.router)

app.include_router(stats.router)

app.include_router(health.router)

app.include_router(folders.router)

app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(departments.router)
app.include_router(teams.router)
app.include_router(model_config.router)

@app.get("/")
async def home():
    return{"message":"企业AI知识库助手运行成功"}

