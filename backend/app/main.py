"""Exact three-endpoint API contract. No extra application endpoints."""
import asyncio
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import Settings
from .database import MessageStore
from .gateway import LiteLLMGateway, AllProvidersUnavailable, ProviderRequestFailed, parse_simulation

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=8000)

    @field_validator("session_id", "message", mode="before")
    @classmethod
    def reject_blank(cls, value: str):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("Cannot be empty")
        return value


class ChatMetadata(BaseModel):
    resolution_source: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]


def create_app(settings: Settings | None = None, store: MessageStore | None = None, gateway=None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store or MessageStore(settings.database_url)
    if gateway is None and settings.llm_api_keys:
        gateway = LiteLLMGateway(settings.llm_api_keys, settings.model, settings.request_timeout)

    app = FastAPI(title="Relay API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Simulate-Failure"])
    # Serialize concurrent chats in a single session to preserve conversation ordering.
    session_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]})

    @app.exception_handler(Exception)
    async def unknown_error(request: Request, exc: Exception):
        logger.exception("Unexpected API failure")
        return JSONResponse(status_code=503, content={"detail": "service temporarily unavailable"})

    @app.get("/health")
    async def health():
        if len(settings.llm_api_keys) < 2 or gateway is None or not store.ready():
            raise HTTPException(status_code=503, detail="service temporarily unavailable")
        return {"status": "ok", "keys_configured": len(settings.llm_api_keys), "cache_enabled": True}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, x_simulate_failure: Annotated[str | None, Header()] = None):
        if len(settings.llm_api_keys) < 2 or gateway is None:
            raise HTTPException(status_code=503, detail="all providers unavailable")
        started = time.perf_counter()
        async with session_locks[payload.session_id]:
            previous = store.get_history(payload.session_id)
            prompt = payload.system_prompt if payload.system_prompt is not None else (store.get_prompt(payload.session_id) or settings.default_system_prompt)
            messages = [{"role": "system", "content": prompt}]
            messages.extend({"role": m["role"], "content": m["content"]} for m in previous)
            messages.append({"role": "user", "content": payload.message})
            simulation = parse_simulation(x_simulate_failure) if settings.enable_failure_simulation else {}
            try:
                answer = await gateway.complete(messages, simulation)
            except AllProvidersUnavailable:
                raise HTTPException(status_code=503, detail="all providers unavailable") from None
            except ProviderRequestFailed:
                raise HTTPException(status_code=503, detail="service temporarily unavailable") from None
            elapsed = max(0, round((time.perf_counter() - started) * 1000))
            metadata = ChatMetadata(
                resolution_source=answer.source,
                model=answer.model,
                latency_ms=elapsed,
                input_tokens=answer.input_tokens,
                output_tokens=answer.output_tokens,
                key_id=answer.key_id,
                fallback_attempts=answer.fallback_attempts,
            )
            store.save_exchange(payload.session_id, payload.message, answer.reply, metadata.model_dump(), prompt)
            return ChatResponse(session_id=payload.session_id, reply=answer.reply, metadata=metadata)

    @app.get("/sessions/{session_id}/messages", response_model=HistoryResponse)
    async def history(session_id: str = Path(min_length=1, max_length=128)):
        messages = store.get_history(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="session not found")
        return HistoryResponse(session_id=session_id, messages=messages)

    return app


app = create_app()
