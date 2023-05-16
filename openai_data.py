def build_chunk_data(id, created, model, content):
    return {
        "id": id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "delta": {"content": content},
                "index": 0,
                "finish_reason": "stop",
            }
        ],
    }


def build_comp_data(id, created, model, text, prop_len, comp_len, total_tokens):
    """build completion response data"""
    return {
        "id": id,
        "object": "text_completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "text": text,
                "index": 0,
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prop_len,
            "completion_tokens": comp_len,
            "total_tokens": total_tokens,
        },
    }


def build_chat_comp_data(
    id, created, model, resp_content, prompt_tokens, completion_tokens
):
    """build chat completion response data"""
    return {
        "id": id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": resp_content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
