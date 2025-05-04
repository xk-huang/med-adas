dataset_name_list=(
'AfrimedQA'
'MMLU'
'MMLU-Pro'
'MedBullets'
'MedExQA'
'MedMCQA'
'MedQA'
'PubMedQA'
)

for dataset_name in "${dataset_name_list[@]}"; do
    echo "Running search for dataset: ${dataset_name}"
done

for dataset_name in "${dataset_name_list[@]}"; do
    echo "Running search for dataset: ${dataset_name}"
    AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
    AZURE_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
    python src/adas/search.py --dataset_name "${dataset_name}"
done

for dataset_name in "${dataset_name_list[@]}"; do
    echo "Running search for dataset: ${dataset_name}"
    AZURE_META_AGENT_MODEL="gpt-4o-1120-nofilter-global" \
    AZURE_AGENT_MODEL="gpt-4o-mini-20240718-nofilter" \
    python src/adas/search.py --dataset_name "${dataset_name}"
done