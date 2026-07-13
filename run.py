"""Run the local LitRes library downloader on 127.0.0.1 only."""
from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    load_dotenv()
    uvicorn.run("app.web:app", host="127.0.0.1", port=8420, reload=True)
