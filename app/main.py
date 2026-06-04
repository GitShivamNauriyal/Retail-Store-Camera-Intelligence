# FastAPI main entrypoint for the Store Intelligence API
from fastapi import FastAPI

app = FastAPI(title="Store Intelligence API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Store Intelligence API is running"}
