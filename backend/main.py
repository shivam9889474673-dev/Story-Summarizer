import os
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError, OpenAI
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompt.txt"
DATABASE_PATH = BACKEND_DIR / "prompt_store.db"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
if not ENV_FILE.exists():
    ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)

class StoryRequest(BaseModel):
    story: str = Field(min_length=1)


class SummaryResponse(BaseModel):
    summary: str


def initialize_database() -> None:
    seed_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not seed_prompt:
        raise RuntimeError(f"The prompt seed file is empty: {PROMPT_PATH}")

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prompts (
                    name TEXT PRIMARY KEY,
                    content TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO prompts (name, content) VALUES (?, ?)",
                ("story_summary", seed_prompt),
            )


def get_summary_prompt() -> str:
    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            row = connection.execute(
                "SELECT content FROM prompts WHERE name = ?",
                ("story_summary",),
            ).fetchone()
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail="The story prompt is unavailable. Please try again later.",
        ) from error

    prompt = row[0].strip() if row else ""
    if not prompt:
        raise HTTPException(
            status_code=500,
            detail="The story prompt is unavailable. Please try again later.",
        )
    return prompt


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Story Summarizer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.post("/api/summarize", response_model=SummaryResponse)
def summarize_story(request: StoryRequest) -> SummaryResponse:
    story = request.story.strip()
    if not story:
        raise HTTPException(status_code=422, detail="Please enter a story to summarize.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="The summarization service is not configured. Please try again later.",
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    prompt = get_summary_prompt()
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": story},
            ],
        )
        summary = response.choices[0].message.content
    except APIError as error:
        raise HTTPException(
            status_code=502,
            detail="The summarization service could not process your story. Please try again.",
        ) from error

    if not summary or not summary.strip():
        raise HTTPException(
            status_code=502,
            detail="The summarization service returned an empty result. Please try again.",
        )

    return SummaryResponse(summary=summary.strip())
