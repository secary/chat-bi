"""Runtime LLM configuration stored in MySQL (overrides env)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend import llm_settings_repo

router = APIRouter(prefix="/admin", tags=["admin"])


class LlmSettingsPut(BaseModel):
    model: Optional[str] = Field(default=None, max_length=255)
    api_base: Optional[str] = Field(default=None, max_length=512)
    api_key: Optional[str] = Field(default=None, max_length=512)


@router.get("/llm-settings")
def get_llm_settings() -> dict:
    return llm_settings_repo.public_view(llm_settings_repo.get_row())


@router.put("/llm-settings")
def put_llm_settings(body: LlmSettingsPut) -> dict:
    data = body.model_dump(exclude_unset=True)
    llm_settings_repo.save_merged(
        model=data.get("model"),
        api_base=data.get("api_base"),
        api_key=data.get("api_key"),
    )
    return llm_settings_repo.public_view(llm_settings_repo.get_row())
