from datasets import get_dataset_config_names, load_dataset

# Replace 'dataset_name' with the name of the dataset you want to inspect
dataset_name = "xk-huang/medagents-benchmark"

# List all subsets (configurations) of the dataset
subsets = get_dataset_config_names(dataset_name)

print(f"Split information for each subset of the dataset '{dataset_name}':")
for subset in subsets:
    # Load the subset
    dataset = load_dataset(dataset_name, subset)

    # List the available splits
    splits = dataset.keys()
    # the number of examples in each split
    num_examples = {split: len(dataset[split]) for split in splits}
    print(f"Subset: {subset}, Number of examples: {num_examples}")
