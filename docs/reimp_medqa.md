debug data loading

```bash
python src/adas/load_data.py
%run src/adas/load_data.py
```

debug search

```bash
DEBUG_API=1 \
DEBUG=1 \
AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
python src/adas/search.py \
--valid_size 5 \
--test_size 10 \
--n_generation 2


AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-mini-20240718-nofilter" \
python src/adas/search.py \
--valid_size 5 \
--test_size 10 \
--n_generation 2
```


Full run

```bash
AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
python src/adas/search.py


AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
AZURE_AGENT_MODEL="gpt-4o-mini-20240718-nofilter" \
python src/adas/search.py
```