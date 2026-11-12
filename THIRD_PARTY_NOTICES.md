# Third-party notices

This repository is released under the MIT License (see `LICENSE`). It builds on the
work below.

## ReasoningBank (prompts adapted)

- Source: https://github.com/google-research/reasoning-bank (commit `ed80611`, 2026-05-18)
- Paper: Ouyang et al., *ReasoningBank: Scaling Agent Self-Evolving with Reasoning
  Memory*, ICLR 2026, https://arxiv.org/abs/2509.25140
- License: Apache License 2.0, Copyright 2026 Google LLC

The prompt texts in `src/self_evolving_agents/reasoningbank/prompts.py` are adapted
from `WebArena/prompts/memory_instruction.py` and `WebArena/prompts/autoeval_prompts.py`
of that repository. `MEMORY_INSTRUCTION` is quoted unchanged; the extraction, judging
and scaling prompts were modified, and the module docstring lists the changes. Those
adapted texts remain subject to the Apache License 2.0
(https://www.apache.org/licenses/LICENSE-2.0). No other code was copied; the memory
schema, retrieval, pipeline and test-time-scaling logic were written for this
repository following the paper and the reference implementation's behaviour.

## Used as dependencies (not redistributed)

| Project | Use here | License |
|---|---|---|
| [BSK-RL](https://github.com/AVSLab/bsk_rl) (AVS Lab, CU Boulder) | Gymnasium spacecraft-tasking environments; the `bsk-scan` adapter follows its nadir-scanning example | MIT |
| [Basilisk](https://github.com/AVSLab/basilisk) | Astrodynamics simulation underneath BSK-RL | ISC |
| [DiscoveryWorld](https://github.com/allenai/discoveryworld) (Allen Institute for AI) | Scientific-discovery environment behind the `discoveryworld` adapter | Apache 2.0 |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | Claude backend | MIT |
| NumPy | Embeddings and statistics | BSD-3-Clause |

Basilisk downloads NASA NAIF SPICE kernels (`de430.bsp` and others) from
`naif.jpl.nasa.gov` on first use; they are not part of this repository.
