from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import get_session, initialize_database
from app.routers.auth import router as auth_router
from app.routers.analytics import router as analytics_router
from app.routers.catalog import router as catalog_router
from app.routers.papers import router as papers_router
from app.routers.semantic import router as semantic_router
from app.services.pgvector_search import SentenceTransformerUnavailableError


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    if get_session not in _app.dependency_overrides:
        initialize_database()
    yield


app = FastAPI(
    title="Historical Examination Pattern Analysis API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SentenceTransformerUnavailableError)
async def sentence_transformer_unavailable(
    _: Request,
    exc: SentenceTransformerUnavailableError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")


@app.get("/")
def read_root() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


app.include_router(catalog_router)
app.include_router(papers_router)
app.include_router(analytics_router)
app.include_router(semantic_router)
app.include_router(auth_router)
