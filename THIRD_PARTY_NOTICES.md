# Third-party notices

This repository is released under the MIT License (see `LICENSE`). It builds on the
work below.

## ReasoningBank (prompts quoted)

- Paper: Ouyang et al., *ReasoningBank: Scaling Agent Self-Evolving with Reasoning
  Memory*, ICLR 2026, https://arxiv.org/abs/2509.25140 (v2)
- Reference implementation: https://github.com/google-research/reasoning-bank
  (commit `ed80611`, 2026-05-18)
- License of the reference implementation: Apache License 2.0, Copyright 2026 Google LLC

Prompt texts are quoted from the paper's figures and appendix, and agree with the
reference implementation where it contains them. The texts that appear in the
reference implementation remain subject to the Apache License 2.0
(https://www.apache.org/licenses/LICENSE-2.0). The Best-of-N prompt appears only in
the paper and is quoted from it, with attribution, to reproduce the method. Each
module's docstring lists every change made to the published text.

| File in `src/self_evolving_agents/methods/` | Text | Source | Changes |
|---|---|---|---|
| `reasoningbank/prompts.py` | instruction placed before retrieved memory items | paper, Appendix A.2; reference code `WebArena/agents/legacy/agent.py` | none |
| `reasoningbank/prompts.py` | memory extraction from a successful and from a failed trajectory | paper, Figure 9; reference code `third_party/src/minisweagent/memory/instruction.py` | "web navigation" replaced by the environment's domain |
| `reasoningbank/prompts.py` | later revisions of the extraction notes and the judge's strictness rules (off by default) | reference code `WebArena/prompts/memory_instruction.py`, `autoeval_prompts.py` | domain substitution |
| `reasoningbank/prompts.py` | LLM-as-a-judge | paper, Figure 10; reference code `WebArena/prompts/autoeval_prompts.py` | the description of three kinds of web task is replaced by the environment's success criterion |
| `matts/prompts.py` | self-contrast extraction; check instructions of sequential scaling (kept for reference, unused) | paper, Figure 11; reference code `WebArena/prompts/memory_instruction.py` | domain substitution |
| `matts/prompts.py` | Best-of-N selection | paper, Figure 12 (not in the reference code) | domain substitution |
| `policy_program/prompts.py` | memory instruction for an agent that writes one policy | derived from Appendix A.2 | last sentence rewritten |

No other code was copied. The memory schema, retrieval, loop and test-time scaling
were written for this repository from the paper and from the reference
implementation's observed behaviour; the comparison row by row is in
`docs/reasoningbank-fidelity.md`.

## Used as dependencies (not redistributed)

| Project | Use here | License |
|---|---|---|
| [BSK-RL](https://github.com/AVSLab/bsk_rl) (AVS Lab, CU Boulder) | Gymnasium spacecraft-tasking environments; the `bsk-scan` adapter follows its nadir-scanning example | MIT |
| [Basilisk](https://github.com/AVSLab/basilisk) | Astrodynamics simulation underneath BSK-RL | ISC |
| [DiscoveryWorld](https://github.com/allenai/discoveryworld) (Allen Institute for AI) | Scientific-discovery environment behind the `discoveryworld` adapter | Apache 2.0 |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | Claude backend | MIT |
| [google-genai](https://github.com/googleapis/python-genai) | optional: the embedding model the paper used | Apache 2.0 |
| NumPy | Embeddings and statistics | BSD-3-Clause |

Basilisk downloads NASA NAIF SPICE kernels (`de430.bsp` and others) from
`naif.jpl.nasa.gov` on first use; they are not part of this repository.
