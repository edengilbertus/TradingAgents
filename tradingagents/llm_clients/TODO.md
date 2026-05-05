# LLM Clients - Consistency Improvements

## All Issues Resolved

### 1. ~~`validate_model()` is never called~~ (Fixed)
- `warn_if_unknown_model()` is called as the first line of `get_llm()` in all
  four client classes: `OpenAIClient`, `AnthropicClient`, `GoogleClient`,
  `AzureOpenAIClient`.

### 2. ~~Inconsistent parameter handling~~ (Fixed)
- GoogleClient now accepts unified `api_key` and maps it to `google_api_key`

### 3. ~~`base_url` accepted but ignored~~ (Fixed)
- All clients now pass `base_url` to their respective LLM constructors

### 4. ~~Update validators.py with models from CLI~~ (Fixed)
- Synced in v0.2.2
