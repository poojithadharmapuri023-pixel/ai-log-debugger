from fastapi import FastAPI

app = FastAPI(
    title="AI Log Debugger",
    description="Automated log analysis and root cause detection system",
    version="0.1.0"
)


@app.get("/")
def home():
    return {
        "message": "AI Log Debugger is running!"
    }
