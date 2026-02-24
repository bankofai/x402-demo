"""A2A ↔ GenAI Part type conversion utilities."""

import json

from a2a.types import DataPart, FilePart, FileWithBytes, FileWithUri, Part, TextPart
from google.genai import types


def a2a_to_genai(parts: list[Part]) -> list[types.Part]:
    return [_a2a_to_genai_one(p) for p in parts]


def genai_to_a2a(parts: list[types.Part]) -> list[Part]:
    return [
        _genai_to_a2a_one(p) for p in parts
        if p.text or p.file_data or p.inline_data or p.function_response
    ]


# --- Internal ---

def _a2a_to_genai_one(part: Part) -> types.Part:
    p = part.root
    if isinstance(p, TextPart):
        return types.Part(text=p.text)
    if isinstance(p, DataPart):
        return types.Part(text=f"Received structured data:\n```json\n{json.dumps(p.data)}\n```")
    if isinstance(p, FilePart):
        if isinstance(p.file, FileWithUri):
            return types.Part(file_data=types.FileData(file_uri=p.file.uri, mime_type=p.file.mimeType))
        if isinstance(p.file, FileWithBytes):
            return types.Part(inline_data=types.Blob(data=p.file.bytes, mime_type=p.file.mimeType))
    raise ValueError(f"Unsupported A2A part type: {type(p)}")


def _genai_to_a2a_one(part: types.Part) -> Part:
    if part.text:
        return Part(root=TextPart(text=part.text))
    if part.file_data:
        return Part(root=FilePart(file=FileWithUri(uri=part.file_data.file_uri, mimeType=part.file_data.mime_type)))
    if part.inline_data:
        return Part(root=FilePart(file=FileWithBytes(bytes=part.inline_data.data, mimeType=part.inline_data.mime_type)))
    if part.function_response:
        return Part(root=DataPart(data=part.function_response.response))
    raise ValueError(f"Unsupported GenAI part type: {part}")
