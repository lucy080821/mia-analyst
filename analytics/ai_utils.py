"""
AI Utility Module — Centralized model resolution for Gemini API.
Eliminates 404 errors by dynamically selecting available models.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache to avoid calling list_models on every request
_cached_model = None
_cache_timestamp = 0


def get_safe_model_name() -> str:
    """
    Returns a valid, available Gemini model name.
    Uses settings.AI_MODEL_NAME as primary, falls back through AI_FALLBACK_MODELS.
    Caches result for 10 minutes to avoid excessive API calls.
    """
    import time
    import google.generativeai as genai
    global _cached_model, _cache_timestamp

    # Return cached model if fresh (< 10 minutes)
    if _cached_model and (time.time() - _cache_timestamp) < 600:
        return _cached_model

    genai.configure(api_key=settings.GEMINI_API_KEY)

    # Build candidate list: primary model + fallbacks
    candidates = [settings.AI_MODEL_NAME]
    fallbacks = getattr(settings, 'AI_FALLBACK_MODELS', [])
    for fb in fallbacks:
        if fb not in candidates:
            candidates.append(fb)

    # Normalize: ensure all candidates have "models/" prefix for comparison
    def normalize(name):
        return name if name.startswith('models/') else f'models/{name}'

    try:
        available_models = [
            m.name for m in genai.list_models()
            if 'generateContent' in m.supported_generation_methods
        ]

        for candidate in candidates:
            normalized = normalize(candidate)
            if normalized in available_models:
                _cached_model = candidate
                _cache_timestamp = time.time()
                logger.info(f"AI Model resolved: {candidate}")
                return candidate

        # If none of our candidates are available, pick first available model
        if available_models:
            # Prefer flash models for speed
            for m in available_models:
                if 'flash' in m.lower():
                    model_name = m.replace('models/', '')
                    _cached_model = model_name
                    _cache_timestamp = time.time()
                    logger.warning(f"No preferred model found, using: {model_name}")
                    return model_name

            # Last resort: first available model
            model_name = available_models[0].replace('models/', '')
            _cached_model = model_name
            _cache_timestamp = time.time()
            logger.warning(f"Using first available model: {model_name}")
            return model_name

    except Exception as e:
        logger.error(f"Failed to list models: {e}")

    # Ultimate fallback — return the configured model and hope for the best
    return settings.AI_MODEL_NAME


def get_generative_model(model_name: str = None):
    """
    Returns a configured GenerativeModel instance using a safe, available model.
    If model_name is provided, sanitizes it first; otherwise auto-resolves.
    """
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    if model_name:
        # Sanitize: fix common unicode dash issues
        safe_name = model_name.replace('\u2013', '-').replace('\u2014', '-')
    else:
        safe_name = get_safe_model_name()

    return genai.GenerativeModel(safe_name)
