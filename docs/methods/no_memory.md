# No memory (reference point)

**Origin:** the "No Memory" (vanilla) baseline of the ReasoningBank paper.
**Code:** `methods/no_memory/` (a name for the stream loop's default memory).
**Evidence in this repository:** verified for correctness with scripted stand-ins;
never run with a language model.

## Motivation

Every claim that a memory helps is a claim relative to the same agent without one.
This is that agent.

## The method

The agent meets each task of the stream as if it were the first. Nothing is
retrieved, nothing is put into the system prompt, nothing is learned afterwards, and
by default no judge is called.

## Implementation

There is nothing to implement. `methods/stream.py` defines the memory interface, and
its base class retrieves nothing and learns nothing; `methods/no_memory` gives that
class its name. The agent, the prompts for acting, the environments and the loop are
exactly those every other stream method uses.

## Differences from the ReasoningBank baseline

No retrieval, no memory instruction in the prompt, no judge, no extraction, no bank.
Everything else is identical, which is what makes the comparison meaningful.

## Parameters

| Option | Default | Meaning |
|---|---|---|
| `judge` | `none` | `none`: no judge calls. `llm` or `env`: judge the episodes anyway, to measure how well a judge agrees with the simulator without any memory being built from its labels |

## Assumptions and dependencies

None of its own. It uses the shared agent, environments and loop, and a language
model.

## Running it

```bash
sea run --method no_memory --env toy-scan --regime nominal,small_battery --order interleaved --seeds 0:3 --llm offline-demo --out runs/none-dry
```

It is the first arm of every protocol in `protocols/`.

## Expected behaviour and limitations

With a language model, performance should not change over a stream: the mean score
of the second half should equal that of the first half up to noise. If it does
change, the stream's tasks differ systematically between its halves, and a "learning
curve" of any other method on that stream has to be read against this one.

A run of this method uses about the same number of model calls as any other
step-by-step method minus two per task (judge and extraction). The paper reports the
no-memory agent at 50,847 tokens per task against 53,055 for ReasoningBank on its
benchmark.
