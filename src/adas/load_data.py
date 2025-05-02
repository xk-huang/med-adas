import dotenv

dotenv.load_dotenv(override=True)


from argparse import Namespace

from datasets import concatenate_datasets, load_dataset


def load_samples(args, mode: str):
    MODE_MAPPING = {
        "search": "test_hard_leftout",
        "evaluation": "test_hard",
    }
    """
    Load samples from the dataset based on the specified mode.
    
    Args:
        args: Command line arguments containing the dataset path.
        mode (str): The mode to load samples for. Can be 'train', 'test', or 'val'.
    
    Returns:
        list: A list of loaded samples.
    """
    dataset_path = args.dataset_path
    dataset_name = args.dataset_name
    valid_size = args.valid_size
    test_size = args.test_size
    n_repeat = args.n_repeat
    shuffle_seed = args.shuffle_seed
    if mode not in MODE_MAPPING:
        raise ValueError(
            f"Invalid mode: {mode}. Choose from {list(MODE_MAPPING.keys())}."
        )
    split = MODE_MAPPING[mode]

    print(f"Loading {mode} samples from {dataset_path}/{dataset_name} dataset...")
    print(
        f"Split: {split}, Valid Size: {valid_size}, Test Size: {test_size}, Repeat: {n_repeat}, Shuffle Seed: {shuffle_seed}"
    )

    # load the dataset
    dataset = load_dataset(dataset_path, dataset_name)[split]
    print(f"Loaded {len(dataset)} samples from the dataset.")

    # Select a subset of the dataset based on the mode
    if mode == "search":
        dataset = dataset.shuffle(seed=shuffle_seed).select(range(valid_size))
    elif mode == "evaluation":
        dataset = dataset.shuffle(seed=shuffle_seed).select(range(test_size))
    print(f"Select {len(dataset)} samples.")

    # repeat the dataset
    dataset = concatenate_datasets([dataset] * n_repeat)
    print(f"Repeat {n_repeat} times, total samples: {len(dataset)}")

    questions = []
    answers = []

    for sample in dataset:
        question = sample["question"]
        options = sample["options"]
        answer = sample["answer"]
        answer_idx = sample["answer_idx"]

        if options[answer_idx] != answer:
            raise ValueError(
                f"Answer {answer_idx}: {answer} does not match the option {options[answer_idx]}."
            )
        str_format_input_dict = {
            "Question": question,
            "Options": "\n".join(
                [f"({key}) {value}" for key, value in options.items()]
            ),
        }

        question_str = format_multichoice_question(str_format_input_dict)
        questions.append(question_str)

        answers.append(answer_idx)

    return questions, answers


QUERY_TEMPLATE_MULTICHOICE = """
Answer the following multiple choice question.

{Question}

{Options}
""".strip()


def format_multichoice_question(row):
    return QUERY_TEMPLATE_MULTICHOICE.format(**row)


def main():
    args = Namespace(
        dataset_path="xk-huang/medagents-benchmark",
        dataset_name="MedQA",
        valid_size=128,
        test_size=800,
        shuffle_seed=0,
        n_repeat=1,
    )
    questions, answers = load_samples(args, "search")
    breakpoint()


if __name__ == "__main__":
    main()
