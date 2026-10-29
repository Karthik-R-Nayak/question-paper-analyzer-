from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers.analytics import router as analytics_router
from app.routers.catalog import router as catalog_router
from app.routers.papers import router as papers_router
from app.routers.semantic import router as semantic_router

app = FastAPI(
    title="Historical Examination Pattern Analysis API",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")


@app.get("/")
def read_root() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


app.include_router(catalog_router)
app.include_router(papers_router)
app.include_router(analytics_router)
app.include_router(semantic_router)
