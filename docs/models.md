# Language models and embedders

Every component that calls a language model takes it from one place
(`src/self_evolving_agents/llm/`), and every component that embeds text takes the
embedder from one place (`embeddings.py`). So any backend below works for every
method (ReasoningBank, MaTTS, the adaptations, claims as memory), for the judge and
the extractor, for the claim graph's hypothesis proposer, and in every protocol.

**Status.** Each backend has been exercised through its official client library
against a local stand-in server, and the Hugging Face backends against tiny models
built on the spot with random weights. No real model has been reached from this
repository: the network of the environment it was built in does not allow model
hosts. The first real run of each backend may need adjustment.

## Choosing a model

One description, on the command line (`--llm`) and in protocols (`"llm"`):

| Description | Backend | Notes |
|---|---|---|
| `anthropic:<model>` | Claude, official `anthropic` SDK | the default; `--effort` applies here only |
| `openai:<model>` | OpenAI, official `openai` SDK | key in `OPENAI_API_KEY` |
| `openai:<model>@<address>` | any OpenAI-compatible server | vLLM, llama.cpp, LM Studio, text-generation-inference, Together, Groq, OpenRouter, the Hugging Face router, Ollama's `/v1` |
| `ollama:<model>` | Ollama's own API, official `ollama` client | `OLLAMA_HOST` or `127.0.0.1:11434` |
| `ollama:<model>@<address>` | an Ollama server elsewhere | |
| `hf:<model>` | a model run on this machine with `transformers` | a Hub id or a local directory |
| `offline-demo` | a rule-based stand-in | **not a language model**; for dry runs |

Model names may contain colons and slashes (`ollama:llama3.2:3b`,
`hf:Qwen/Qwen2.5-7B-Instruct`). The address is recognised by its `http://` or
`https://`.

Options go to the backend: `--llm-option NAME=VALUE` (repeatable), or
`"llm_options": {...}` next to `"llm"` in a protocol's `model` section. Values are
read as JSON where they can be (`16384`, `false`, `{"top_k": 20}`).

```bash
sea run --method reasoningbank --env toy-scan --seeds 0:3 --llm ollama:qwen2.5:7b --llm-option num_ctx=32768 --out runs/rb-ollama
```

```bash
sea run --method reasoningbank --env toy-scan --seeds 0:3 --llm openai:Qwen/Qwen2.5-7B-Instruct@http://localhost:8000/v1 --out runs/rb-vllm
```

```bash
sea compare run --protocol protocols/scan_policy_agent.json --out runs/policy-hf --llm hf:Qwen/Qwen2.5-7B-Instruct --llm-option device=cuda
```

## Choosing an embedder

The same format for `--embedder` and `"embedder"`, with options through
`--embedder-option` and `"embedder_options"`:

| Description | Embedder |
|---|---|
| `hashing` | word overlap, offline, the default; **not semantic** |
| `gemini` | `gemini-embedding-001`, the ReasoningBank paper's |
| `openai:<model>[@<address>]` | an OpenAI-style `/v1/embeddings` endpoint |
| `ollama:<model>[@<address>]` | Ollama's `/api/embed` |
| `hf:<model>` | `sentence-transformers` on this machine |

Every embedder but `hashing` keeps its vectors in the run directory
(`embeddings.jsonl`), so a text is embedded once and a reloaded memory gets the same
vectors.

## Options of each backend

| Backend | Option | Default | Meaning |
|---|---|---|---|
| openai | `base_url` | from the description | server address |
| | `api_key_env` | `OPENAI_API_KEY` | environment variable holding the key; a local server needs none |
| | `honour_temperature` | `true` | send the request's temperature; switch off for models that reject it |
| | `max_tokens_param` | `max_tokens` | or `max_completion_tokens` (newer OpenAI models) |
| | `max_output_tokens` | none | cap on the reply length, for servers with a small context |
| | `seed` | none | `seed + sample index` is sent; repeatable on servers that honour it |
| | `reasoning_effort` | none | passed through |
| | `price_in`, `price_out` | none | USD per million tokens, for the spend estimate and `--max-cost` |
| | `extra_body` | none | server-specific fields |
| ollama | `host` | from the description | server address |
| | `num_ctx` | 8192 | context window, sent with every call |
| | `max_output_tokens` | 2048 | cap on the reply length |
| | `seed` | none | as above |
| | `think` | model default | `false` switches a thinking model's thinking off |
| | `strict_context` | `true` | refuse a call whose prompt filled the window |
| | `options` | none | further Ollama options |
| hf | `device` | `auto` | `cpu`, `cuda`, `cuda:1`, `mps` |
| | `dtype` | `auto` | `float16`, `bfloat16`, ... |
| | `revision` | none | a commit of the model repository; pin it for repeatable runs |
| | `seed` | 0 | base of the generation seed |
| | `max_output_tokens` | 2048 | cap on the reply length |
| | `default_temperature` | none (greedy) | used when a request names none |
| | `chat_template_kwargs` | none | e.g. `{"enable_thinking": false}` |

Embedders: `dimensions`, `batch_size` (openai); `batch_size`, `options` (ollama);
`device`, `prefix`, `revision`, `batch_size` (hf).

## What differs between backends, and why it matters for the experiments

**Decoding temperature.** ReasoningBank specifies 0.7 for acting, 0.0 for judging and
1.0 for extraction. The Claude models used by default accept no temperature, so those
values cannot be set there. The OpenAI-compatible, Ollama and Hugging Face backends
apply them. A test checks that a ReasoningBank run through an OpenAI-compatible
server sends exactly these three values. The applied temperature and seed of every
call are stored with it in `provenance.sqlite` (`request.applied`).

**Repeatability.** Hosted models are not deterministic. With a seed, an
OpenAI-compatible server may or may not honour it; Ollama does on the same hardware;
a Hugging Face model does on the same hardware and library versions (a test checks
this). Every call is cached on disk regardless, so rerunning a command replays it.
The cache key includes what decides the reply besides the prompt (temperature,
seed, address), so changing one of these is not answered from the cache.

**Context length.** Small local models have small windows. A prompt that does not
fit is an error in every backend here, never a silent cut: Ollama would otherwise
truncate without saying so, and the result of such a run would be meaningless. The
DiscoveryWorld agents send long observations; set `num_ctx` (Ollama) to at least
16384 for them, and check that the model supports it.

**Cost.** Ollama and Hugging Face models are counted at zero. For an
OpenAI-compatible server, give `price_in` and `price_out` if you want an estimate or
a cost limit; without them `--max-cost` refuses to run and `--max-calls` should be
used instead.

**Hosted Hugging Face models** are reached through the OpenAI-compatible backend:
`openai:<model>@https://router.huggingface.co/v1` with `api_key_env=HF_TOKEN`.

## Installing

```bash
pip install -e ".[openai,ollama]"
```

```bash
pip install -e ".[huggingface]"
```

The `all` extra includes `openai` and `ollama` but not `huggingface`, which brings
PyTorch.
