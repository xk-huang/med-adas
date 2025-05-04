# med-adas

Method: Automated Design of Agentic Systems https://www.shengranhu.com/ADAS/


## Env

Install env:

```bash
conda create -n adas -y python=3.11
conda activate adas

pip install uv
uv pip install -r requirements.txt
```

Set up `.env` for environment variables

touch `.env`, and add those vars:

Replace `?????` with yours.

```
HF_HOME=cache/

AZURE_API_KEY=?????
AZURE_ENDPOINT==?????
AZURE_API_VERSION==?????
```

This is used to create client in `src/adas/search.py:L22-34`.
You can change to other methods by yourself.

## Data

Paper: MedAgentsBench: Benchmarking Thinking Models and Agent Frameworks for Complex Medical Reasoning https://arxiv.org/abs/2503.07459

The dataset processed for our project: https://huggingface.co/datasets/xk-huang/medagents-benchmark

By default, we use `MedQA` subset.
- The "test_hard" is used for testing (only run at the end of the training)
- The "test_hard_leftout" is used for validation, used after each iteration to provide feedback for the auto designed agents.



## Experiment

To run the code:
You need to `AZURE_META_AGENT_MODEL` and `AZURE_AGENT_MODEL` to your deployed model names:
- AZURE_META_AGENT_MODEL: is used for the meta agent, which writes/refines agents with codes.
- AZURE_AGENT_MODEL: is used by the written code agents, the agents that evolved by meta agent. Use 4o-mini to save cost.

```bash
# To debug both api and agent output
# Search "breakpoint" in the `src/adas/search.py`
DEBUG_API=1 \
DEBUG=1 \
AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
python src/adas/search.py \
--valid_size 5 \
--test_size 10 \
--n_generation 2


# To debug agent output
# Search "breakpoint" in the `src/adas/search.py`
DEBUG=1 \
AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
python src/adas/search.py \
--valid_size 5 \
--test_size 10 \
--n_generation 2

# Fast run for only 2 iteration with 5 validation samples and 10 test samples
DEBUG=1 \
AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
python src/adas/search.py \
--valid_size 5 \
--test_size 10 \
--n_generation 2


# Full run
# I would recommend you use 4o-mini for AZURE_AGENT_MODEL
AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
python src/adas/search.py
```

To run the full experiments, see `scripts/experiments/run.sh`.

## Misc

~~Check https://github.com/xk-huang/ADAS/tree/main/docs for env and re-implementation.~~
