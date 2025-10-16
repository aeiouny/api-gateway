from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def index():
    return {"message": "API Gateway is running!"}