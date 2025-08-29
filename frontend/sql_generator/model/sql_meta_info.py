# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from pydantic import BaseModel, ConfigDict

class SQLMetaInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    SQL: str = ""
    plan: str = ""
    chain_of_thought_reasoning: str = ""
    error: str = ""
