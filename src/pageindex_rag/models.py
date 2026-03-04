import sys
from typing import Optional

from .config import get_model


_model = None
_tokenizer = None


def load_model(model_path: Optional[str] = None) -> tuple:
    global _model, _tokenizer
    
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer
    
    if model_path is None:
        model_path = get_model()
    
    print(f"Loading model: {model_path}", file=sys.stderr)
    print("This may take a while on first run...", file=sys.stderr)
    
    from mlx_lm import load
    _model, _tokenizer = load(model_path)
    
    print("Model loaded successfully!", file=sys.stderr)
    return _model, _tokenizer


def generate(
    prompt: str,
    model_path: Optional[str] = None,
    max_tokens: int = 512,
) -> str:
    model, tokenizer = load_model(model_path)
    
    from mlx_lm import generate
    
    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
    )
    
    return response


def generate_streaming(
    prompt: str,
    model_path: Optional[str] = None,
    max_tokens: int = 512,
):
    model, tokenizer = load_model(model_path)
    
    from mlx_lm import generate
    
    for response in generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        stream=True,
    ):
        yield response


def clear_model():
    global _model, _tokenizer
    _model = None
    _tokenizer = None
