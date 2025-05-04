"""
Parse the json result file.

python scripts/parse_results.py -i outputs/MedQA_gpt-4o-1120-nofilter-global_results_run_archive_evaluate.json
"""

import json
from pathlib import Path

import click
import matplotlib.pyplot as plt


@click.command()
@click.option(
    "--input_json", "-i", type=Path, required=True, help="Path to the input JSON file."
)
def main(input_json):
    """
    Parse the input JSON file and print the performance metrics.
    """
    # Load the JSON data
    with open(input_json, "r") as f:
        data = json.load(f)

    init_acc = []
    evo_acc = []
    for row in data:
        if row["generation"] == "initial":
            init_acc.append(row["accuracy"])
        else:
            evo_acc.append(row["accuracy"])

    # Plot the evo acc in a line plot, each init acc as scatter points
    fig, ax = plt.subplots()
    ax.plot(evo_acc, label="Evo Acc", marker="o")
    ax.scatter(range(len(init_acc)), init_acc, label="Init Acc", color="red")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Accuracy")
    ax.set_title(f"Evo Acc vs Init Acc\n{input_json.stem}")
    ax.legend()

    output_fig_path = input_json.with_suffix(".png")
    fig.savefig(output_fig_path)
    print(f"Figure saved to {output_fig_path}")


if __name__ == "__main__":
    main()
