"""LLM wrapper for SQL generation via Groq, Ollama, or mock fallback."""

from __future__ import annotations

import itertools
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load project-level environment variables from queryshield/.env.
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)


class LLMError(RuntimeError):
    """Raised when SQL generation fails."""


_api_key_cycle = None

# Per-provider key cycles for multi-key round-robin
_provider_key_cycles: dict[str, itertools.cycle] = {}

class LLMClient:
    """Generate SQL from prompts using a configurable LLM provider."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower().strip()
        self.timeout_seconds = timeout_seconds

        if self.provider == "groq":
            self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            self.base_url = (
                base_url
                or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
            ).rstrip("/")
            api_key_str = api_key or os.getenv("GROQ_API_KEY")
            if not api_key_str:
                raise LLMError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
            self.api_keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
            if not self.api_keys:
                raise LLMError("GROQ_API_KEY must contain at least one valid key.")
            
            global _api_key_cycle
            if _api_key_cycle is None:
                _api_key_cycle = itertools.cycle(self.api_keys)

        elif self.provider == "ollama":
            self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            self.base_url = (
                base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ).rstrip("/")
            self.api_keys = []

        elif self.provider == "gemini":
            self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            self.base_url = "https://generativelanguage.googleapis.com/v1beta"
            api_key_str = api_key or os.getenv("GEMINI_API_KEY")
            if not api_key_str:
                raise LLMError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini. Get one free at https://ai.google.dev")
            self.api_keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
            self._init_key_cycle()

        elif self.provider == "cerebras":
            self.model = model or os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")
            self.base_url = (
                base_url
                or os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
            ).rstrip("/")
            api_key_str = api_key or os.getenv("CEREBRAS_API_KEY")
            if not api_key_str:
                raise LLMError("CEREBRAS_API_KEY is required when LLM_PROVIDER=cerebras. Get one free at https://cloud.cerebras.ai")
            self.api_keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
            self._init_key_cycle()

        elif self.provider == "sambanova":
            self.model = model or os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")
            self.base_url = (
                base_url
                or os.getenv("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1")
            ).rstrip("/")
            api_key_str = api_key or os.getenv("SAMBANOVA_API_KEY")
            if not api_key_str:
                raise LLMError("SAMBANOVA_API_KEY is required when LLM_PROVIDER=sambanova. Get one free at https://cloud.sambanova.ai")
            self.api_keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
            self._init_key_cycle()

        elif self.provider == "mock":
            self.model = "mock-sql"
            self.base_url = "local"
            self.api_keys = []
        else:
            raise LLMError(
                f"Unsupported LLM provider: {self.provider}. "
                "Use groq, ollama, gemini, cerebras, sambanova, or mock."
            )

    def _init_key_cycle(self) -> None:
        """Initialize a per-provider round-robin key cycle."""
        if self.provider not in _provider_key_cycles:
            _provider_key_cycles[self.provider] = itertools.cycle(self.api_keys)

    def generate_sql(self, prompt: str) -> str:
        """Return a single SQL statement for the given prompt."""
        raw = self.generate_text(prompt)
        return self._extract_sql(raw)

    def generate_text(self, prompt: str) -> str:
        """Return raw model text for the given prompt without SQL extraction."""
        if self.provider == "groq":
            return self._generate_with_groq(prompt)
        if self.provider == "ollama":
            return self._generate_with_ollama(prompt)
        if self.provider == "gemini":
            return self._generate_with_gemini(prompt)
        if self.provider in ("cerebras", "sambanova"):
            return self._generate_with_openai_compat(prompt)
        return self._mock_generate_text(prompt)

    def _generate_with_ollama(self, prompt: str) -> str:
        """Call local Ollama server and return model text output."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            print(f"\n[DEBUG] Ollama RequestException: {exc}")
            raise LLMError(
                "Ollama request failed. Ensure Ollama is running and model is pulled "
                "(e.g., `ollama serve` and `ollama pull qwen2.5:3b`)."
            ) from exc
        except ValueError as exc:
            raise LLMError("Invalid JSON response from Ollama.") from exc

        output = data.get("response", "").strip()
        if not output:
            raise LLMError("Ollama returned an empty response.")

        return output

    def _generate_with_groq(self, prompt: str) -> str:
        """Call Groq chat completions endpoint and return model output."""
        import time
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        
        global _api_key_cycle
        max_attempts = max(5, len(self.api_keys) * 3)
        
        for attempt in range(max_attempts):
            selected_api_key = next(_api_key_cycle) if _api_key_cycle else self.api_keys[0]
            headers = {
                "Authorization": f"Bearer {selected_api_key}",
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                
                if response.status_code == 429:
                    try:
                        err_msg = response.json().get("error", {}).get("message", "Rate limit")
                        print(f"[DEBUG] 429 Hit -> Rotating key. Wait 1.5s... ({err_msg[:60]}...)")
                    except:
                        pass
                    time.sleep(1.5)
                    continue  # Try next key
                
                response.raise_for_status()
                data = response.json()
                break  # Success!
                
            except requests.RequestException as exc:
                print(f"\n[DEBUG] Groq RequestException: {exc}. Rotating key...")
                continue
        else:
            raise LLMError("Groq request failed: All API keys exhausted or failing.")

        try:
            output = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected Groq response format.") from exc

        if not output:
            raise LLMError("Groq returned an empty response.")

        return output

    def _generate_with_gemini(self, prompt: str) -> str:
        """Call Google Gemini native REST API (generateContent)."""
        cycle = _provider_key_cycles.get(self.provider)
        max_attempts = max(3, len(self.api_keys) * 2)
        
        for attempt in range(max_attempts):
            selected_key = next(cycle) if cycle else self.api_keys[0]

            url = f"{self.base_url}/models/{self.model}:generateContent?key={selected_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0},
            }

            try:
                response = requests.post(url, json=payload, timeout=self.timeout_seconds)
                response.raise_for_status()
                data = response.json()
                break
            except requests.RequestException as exc:
                print(f"[DEBUG] Gemini error: {exc}. Rotating key...")
                import time
                time.sleep(1)
                continue
        else:
            raise LLMError("Gemini request failed: All API keys exhausted or failing.")

        try:
            output = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected Gemini response format: {data}") from exc

        if not output:
            raise LLMError("Gemini returned an empty response.")

        return output

    def _generate_with_openai_compat(self, prompt: str) -> str:
        """Generic OpenAI-compatible chat completions for Cerebras/SambaNova."""
        import time
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }

        cycle = _provider_key_cycles.get(self.provider)
        max_attempts = max(3, len(self.api_keys) * 2)

        for attempt in range(max_attempts):
            selected_key = next(cycle) if cycle else self.api_keys[0]
            headers = {
                "Authorization": f"Bearer {selected_key}",
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=self.timeout_seconds
                )

                if response.status_code == 429:
                    print(f"[DEBUG] {self.provider} 429 -> Rotating key. Wait 2s...")
                    time.sleep(2)
                    continue

                response.raise_for_status()
                data = response.json()
                break
            except requests.RequestException as exc:
                print(f"[DEBUG] {self.provider} error: {exc}. Rotating key...")
                continue
        else:
            raise LLMError(f"{self.provider}: All API keys exhausted.")

        try:
            output = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected {self.provider} response format.") from exc

        if not output:
            raise LLMError(f"{self.provider} returned an empty response.")

        return output

    def _extract_sql(self, raw_output: str) -> str:
        """
        Normalize model output to one SQL statement.

        This strips markdown code fences and keeps only the first statement.
        """
        text = raw_output.strip()
        fenced = re.findall(r"```[a-zA-Z0-9_-]*\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            text = fenced[0].strip()

        # Fallback: Strip leading rogue language tags if the model forgot backticks
        text = re.sub(r'^(?:sql|sqlite)\s+', '', text, flags=re.IGNORECASE).strip()

        statements = [segment.strip() for segment in text.split(";") if segment.strip()]
        if not statements:
            raise LLMError("Model did not return SQL.")

        return f"{statements[0]};"

    def _mock_generate_sql(self, prompt: str) -> str:
        """Deterministic fallback mode for local testing."""
        question = self._extract_question(prompt).lower()

        if "average" in question and ("marks" in question or "score" in question):
            return (
                "SELECT s.name, ROUND(AVG(sc.marks), 2) AS average_marks "
                "FROM students s "
                "JOIN scores sc ON sc.student_id = s.id "
                "GROUP BY s.id, s.name "
                "ORDER BY average_marks DESC;"
            )

        if "top" in question and ("student" in question or "score" in question):
            return (
                "SELECT s.name, c.title AS course, sc.marks "
                "FROM scores sc "
                "JOIN students s ON s.id = sc.student_id "
                "JOIN courses c ON c.id = sc.course_id "
                "ORDER BY sc.marks DESC "
                "LIMIT 1;"
            )

        if "list" in question and "students" in question:
            return "SELECT id, name, email, department FROM students ORDER BY name;"

        if "course" in question and "average" in question:
            return (
                "SELECT c.title AS course, ROUND(AVG(sc.marks), 2) AS average_marks "
                "FROM scores sc "
                "JOIN courses c ON c.id = sc.course_id "
                "GROUP BY c.id, c.title "
                "ORDER BY average_marks DESC;"
            )

        return (
            "SELECT s.name, c.title AS course, sc.marks "
            "FROM scores sc "
            "JOIN students s ON s.id = sc.student_id "
            "JOIN courses c ON c.id = sc.course_id "
            "ORDER BY s.name, c.title;"
        )

    def _mock_generate_text(self, prompt: str) -> str:
        """Deterministic raw-text fallback for non-SQL prompts."""
        lowered = prompt.lower()
        if "you are a sql validator" in lowered:
            return "VALID"
        return self._mock_generate_sql(prompt)

    @staticmethod
    def _extract_question(prompt: str) -> str:
        """Get the user question section from the composed prompt."""
        marker = "### User Question:"
        sql_marker = "### SQL Query:"

        start_idx = prompt.find(marker)
        if start_idx == -1:
            return prompt.strip()

        start_idx += len(marker)
        end_idx = prompt.find(sql_marker, start_idx)
        if end_idx == -1:
            end_idx = len(prompt)

        return prompt[start_idx:end_idx].strip()
