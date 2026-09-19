from fastapi import FastAPI
from src.routes import auth, contacts

app = FastAPI(title="Contacts REST API")

app.include_router(auth.router)
app.include_router(contacts.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Contacts API"}