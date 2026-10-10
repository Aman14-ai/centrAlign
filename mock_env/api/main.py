from fastapi import FastAPI
from mock_env.api.database import Base, engine
from mock_env.api.routes_api import router as api_router
from mock_env.api.routes_web import router as web_router
from mock_env.api import models  # noqa: ensures models are registered

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mock Company API")
app.include_router(api_router)
app.include_router(web_router)


@app.get("/")
def root():
    return {"message": "Mock Company is running. Visit /app/erp or /docs"}