from fastapi import FastAPI

from app.routers.papers import router as papers_router

app = FastAPI(
    title="Historical Examination Pattern Analysis API",
    version="0.1.0",
)
app.include_router(papers_router)
