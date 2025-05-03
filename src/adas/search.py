import argparse
import copy
import json
import os
import random
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor

import backoff

# client = openai.OpenAI()
import dotenv
import numpy as np
import openai
import pandas
from load_data import load_samples
from med_prompt import get_init_archive, get_prompt, get_reflexion_prompt
from tqdm import tqdm

dotenv.load_dotenv(override=True)

# NOTE(xk): use azure openai
client = openai.AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_key=os.getenv("AZURE_API_KEY"),
    api_version=os.getenv("AZURE_API_VERSION"),
)

# You want to use the local fastapi server
# client = openai.OpenAI(
#     base_url="http://localhost:8000/v1",  # note the /v1 suffix
#     default_headers={"X-Proxy-Key": os.getenv("LOCAL_FAST_API_KEY")},
# )

if os.getenv("DEBUG_API", None) is not None:
    models = [os.getenv("AZURE_META_AGENT_MODEL"), os.getenv("AZURE_AGENT_MODEL")]
    for model in models:
        print(f"Model: {model}")
        test_api_response = client.chat.completions.create(
            model=model,
            messages=[
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello! Who are you?"},
            ],
            temperature=0.5,
            max_tokens=4096,
            stop=None,
        )
        content = test_api_response.choices[0].message.content
        prompt_tokens = test_api_response.usage.prompt_tokens
        completion_tokens = test_api_response.usage.completion_tokens
        print(f"Response: {content}")
        print(f"Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}")
        breakpoint()

from utils import bootstrap_confidence_interval, format_multichoice_question, random_id

Info = namedtuple("Info", ["name", "author", "content", "iteration_idx"])

FORMAT_INST = (
    lambda request_keys: f"""Reply EXACTLY with the following JSON format.\n{str(request_keys)}\nDO NOT MISS ANY REQUEST FIELDS and ensure that your response is a well-formed JSON object!\n"""
)
ROLE_DESC = lambda role: f"You are a {role}."
SYSTEM_MSG = ""

PRINT_LLM_DEBUG = False
SEARCHING_MODE = True


@backoff.on_exception(backoff.expo, openai.RateLimitError)
def get_json_response_from_gpt(msg, model, system_message, temperature=0.5):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": msg},
        ],
        temperature=temperature,
        max_tokens=4096,
        stop=None,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    json_dict = json.loads(content)
    # cost = response.usage.completion_tokens / 1000000 * 15 + response.usage.prompt_tokens / 1000000 * 5
    assert not json_dict is None
    return json_dict


@backoff.on_exception(backoff.expo, openai.RateLimitError)
def get_json_response_from_gpt_reflect(msg_list, model, temperature=0.8):
    response = client.chat.completions.create(
        model=model,
        messages=msg_list,
        temperature=temperature,
        max_tokens=4096,
        stop=None,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    json_dict = json.loads(content)
    assert not json_dict is None
    return json_dict


class LLMAgentBase:
    """
    Attributes:
    """

    def __init__(
        self,
        output_fields: list,
        agent_name: str,
        role="helpful assistant",
        model=None,
        temperature=0.5,
    ) -> None:
        self.output_fields = output_fields
        self.agent_name = agent_name

        self.role = role
        if model is None:
            model = os.getenv("AZURE_AGENT_MODEL")
        self.model = model
        self.temperature = temperature

        # give each instance a unique id
        self.id = random_id()

    def generate_prompt(self, input_infos, instruction) -> str:
        # construct system prompt
        output_fields_and_description = {
            key: (
                f"Your {key}."
                if not "answer" in key
                else f"Your {key}. Return ONLY the alphabet choice, i.e. A or B or C or D."
            )
            for key in self.output_fields
        }
        system_prompt = (
            ROLE_DESC(self.role) + "\n\n" + FORMAT_INST(output_fields_and_description)
        )

        # construct input infos text
        input_infos_text = ""
        for input_info in input_infos:
            if isinstance(input_info, Info):
                (field_name, author, content, iteration_idx) = input_info
            else:
                continue
            if author == self.__repr__():
                author += " (yourself)"
            if field_name == "task":
                input_infos_text += f"# Your Task:\n{content}\n\n"
            elif iteration_idx != -1:
                input_infos_text += (
                    f"### {field_name} #{iteration_idx + 1} by {author}:\n{content}\n\n"
                )
            else:
                input_infos_text += f"### {field_name} by {author}:\n{content}\n\n"

        prompt = input_infos_text + instruction
        return system_prompt, prompt

    def query(self, input_infos: list, instruction, iteration_idx=-1) -> dict:
        system_prompt, prompt = self.generate_prompt(input_infos, instruction)
        try:
            response_json = {}
            response_json = get_json_response_from_gpt(
                prompt, self.model, system_prompt, self.temperature
            )
            assert len(response_json) == len(
                self.output_fields
            ), "not returning enough fields"
        except Exception as e:
            # print(e)
            if "maximum context length" in str(e) and SEARCHING_MODE:
                raise AssertionError(
                    "The context is too long. Please try to design the agent to have shorter context."
                )
            else:
                print(f"Other error in LLM: {e}")

            # try to fill in the missing field
            for key in self.output_fields:
                if not key in response_json and len(response_json) < len(
                    self.output_fields
                ):
                    response_json[key] = ""
            for key in copy.deepcopy(list(response_json.keys())):
                if (
                    len(response_json) > len(self.output_fields)
                    and not key in self.output_fields
                ):
                    del response_json[key]
        output_infos = []
        for key, value in response_json.items():
            info = Info(key, self.__repr__(), value, iteration_idx)
            output_infos.append(info)
        return output_infos

    def __repr__(self):
        return f"{self.agent_name} {self.id}"

    def __call__(self, input_infos: list, instruction, iteration_idx=-1):
        return self.query(input_infos, instruction, iteration_idx=iteration_idx)


class AgentSystem:
    def __init__(self) -> None:
        pass


def search(args):
    file_path = os.path.join(args.save_dir, f"{args.expr_name}_run_archive.json")
    print(f"file_path: {file_path}")

    if os.path.exists(file_path):
        with open(file_path, "r") as json_file:
            archive = json.load(json_file)
        if "generation" in archive[-1] and isinstance(archive[-1]["generation"], int):
            start = archive[-1]["generation"]
        else:
            start = 0
    else:
        archive = get_init_archive()
        start = 0

    for solution in archive:
        if "fitness" in solution:
            continue

        solution["generation"] = "initial"
        print(f"============Initial Archive: {solution['name']}=================")
        try:
            acc_list = evaluate_forward_fn(args, solution["code"])
        except Exception as e:
            print("During evaluating initial archive:")
            print(e)
            continue

        fitness_str = bootstrap_confidence_interval(acc_list)
        solution["fitness"] = fitness_str
        solution["accuracy"] = np.mean(acc_list)

        # save results
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as json_file:
            json.dump(archive, json_file, indent=4)

    for n in range(start, args.n_generation):
        print(f"============Generation {n + 1}=================")
        system_prompt, prompt = get_prompt(archive)
        msg_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            next_solution = get_json_response_from_gpt_reflect(msg_list, args.model)

            Reflexion_prompt_1, Reflexion_prompt_2 = get_reflexion_prompt(
                archive[-1] if n > 0 else None
            )
            # Reflexion 1
            msg_list.append({"role": "assistant", "content": str(next_solution)})
            msg_list.append({"role": "user", "content": Reflexion_prompt_1})
            next_solution = get_json_response_from_gpt_reflect(msg_list, args.model)
            # Reflexion 2
            msg_list.append({"role": "assistant", "content": str(next_solution)})
            msg_list.append({"role": "user", "content": Reflexion_prompt_2})
            next_solution = get_json_response_from_gpt_reflect(msg_list, args.model)
        except Exception as e:
            print("During LLM generate new solution:")
            print(e)
            n -= 1
            continue

        acc_list = []
        for _ in range(args.debug_max):
            try:
                acc_list = evaluate_forward_fn(args, next_solution["code"])
                if np.mean(acc_list) < 0.01 and SEARCHING_MODE:
                    raise Exception("All 0 accuracy")
                break
            except Exception as e:
                print("During evaluation:")
                print(e)
                msg_list.append({"role": "assistant", "content": str(next_solution)})
                msg_list.append(
                    {
                        "role": "user",
                        "content": f"Error during evaluation:\n{e}\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'",
                    }
                )
                try:
                    next_solution = get_json_response_from_gpt_reflect(
                        msg_list, args.model
                    )
                except Exception as e:
                    print("During LLM generate new solution:")
                    print(e)
                    continue
                continue
        if not acc_list:
            n -= 1
            continue

        fitness_str = bootstrap_confidence_interval(acc_list)
        next_solution["fitness"] = fitness_str
        next_solution["accuracy"] = np.mean(acc_list)
        next_solution["generation"] = n + 1

        if "debug_thought" in next_solution:
            del next_solution["debug_thought"]
        if "reflection" in next_solution:
            del next_solution["reflection"]
        archive.append(next_solution)

        # save results
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as json_file:
            json.dump(archive, json_file, indent=4)


def evaluate(args):
    file_path = os.path.join(args.save_dir, f"{args.expr_name}_run_archive.json")
    # NOTE (xk): use rstrip to remove the .json suffix; using strip causes `outputs/*` -> `utputs/*`
    eval_file_path = (
        str(os.path.join(args.save_dir, f"{args.expr_name}_run_archive.json")).rstrip(
            ".json"
        )
        + "_evaluate.json"
    )
    with open(file_path, "r") as json_file:
        archive = json.load(json_file)
    eval_archive = []
    if os.path.exists(eval_file_path):
        with open(eval_file_path, "r") as json_file:
            eval_archive = json.load(json_file)

    current_idx = 0
    while current_idx < len(archive):
        with open(file_path, "r") as json_file:
            archive = json.load(json_file)
        if current_idx < len(eval_archive):
            current_idx += 1
            continue
        sol = archive[current_idx]
        print(f"current_gen: {sol['generation']}, current_idx: {current_idx}")
        current_idx += 1
        try:
            acc_list = evaluate_forward_fn(args, sol["code"])
        except Exception as e:
            print(e)
            continue
        fitness_str = bootstrap_confidence_interval(acc_list)
        sol["test_fitness"] = fitness_str
        sol["accuracy"] = np.mean(acc_list)
        eval_archive.append(sol)

        # save results
        os.makedirs(os.path.dirname(eval_file_path), exist_ok=True)
        with open(eval_file_path, "w") as json_file:
            json.dump(eval_archive, json_file, indent=4)


def evaluate_forward_fn(args, forward_str):
    # dynamically define forward()
    # modified from https://github.com/luchris429/DiscoPOP/blob/main/scripts/launch_evo.py
    namespace = {}
    exec(forward_str, globals(), namespace)
    names = list(namespace.keys())
    if len(names) != 1:
        raise AssertionError(f"{len(names)} things in namespace. Please only provide 1")
    func = namespace[names[0]]
    if not callable(func):
        raise AssertionError(f"{func} is not callable")
    setattr(AgentSystem, "forward", func)

    # map [A-Z] to [0-25]
    LETTER_TO_INDEX = {f"{chr(i + 65)}": i for i in range(26)}
    if SEARCHING_MODE:
        mode = "search"
    else:
        mode = "evaluation"
    questions, answers = load_samples(args, mode)

    print(f"problem length: {len(questions)}")
    max_workers = min(len(questions), args.max_workers) if args.multiprocessing else 1

    task_queue = []
    for q in questions:
        taskInfo = Info("task", "User", q, -1)
        task_queue.append(taskInfo)

    agentSystem = AgentSystem()

    acc_list = []
    if os.getenv("DEBUG", None) is not None:
        response = agentSystem.forward(task_queue[0])
        breakpoint()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(
            tqdm(executor.map(agentSystem.forward, task_queue), total=len(task_queue))
        )

    for q_idx, res in enumerate(results):
        try:
            if isinstance(res, str) and res in LETTER_TO_INDEX:
                predicted_idx = res
            elif isinstance(res, list):
                try_res = res[1]
                predicted_idx = try_res.content
            elif res.content in LETTER_TO_INDEX:
                predicted_idx = res.content
            else:
                print(f"error in q {q_idx}, no matching")
                acc_list.append(0)
                continue
        except Exception as e:
            acc_list.append(0)
            print(f"error in q {q_idx}: {e}")
            continue

        if os.getenv("DEBUG", None) is not None:
            breakpoint()

        if predicted_idx == answers[q_idx]:
            acc_list.append(1)
        else:
            acc_list.append(0)
    print(
        f"acc: {bootstrap_confidence_interval(acc_list)}\nmean acc: {np.mean(acc_list)}"
    )
    return acc_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument('--dataset', type=str, default="MedQA")
    parser.add_argument(
        "--dataset_path", type=str, default="xk-huang/medagents-benchmark"
    )
    parser.add_argument("--dataset_name", type=str, default="MedQA")
    parser.add_argument("--valid_size", type=int, default=128)
    parser.add_argument("--test_size", type=int, default=800)
    parser.add_argument("--shuffle_seed", type=int, default=0)
    parser.add_argument("--n_repeat", type=int, default=1)
    parser.add_argument("--multiprocessing", action="store_true", default=True)
    parser.add_argument("--max_workers", type=int, default=48)
    parser.add_argument("--debug", action="store_true", default=True)
    parser.add_argument("--save_dir", type=str, default="outputs/")
    parser.add_argument("--expr_name", type=str, default=None)
    parser.add_argument("--n_generation", type=int, default=30)
    parser.add_argument("--debug_max", type=int, default=3)
    parser.add_argument("--model", type=str, default=None)

    args = parser.parse_args()

    if args.expr_name is None:
        args.expr_name = f"{args.dataset_name}_{os.getenv('AZURE_AGENT_MODEL')}_results"
    if args.model is None:
        args.model = os.getenv("AZURE_META_AGENT_MODEL")

    print(f"Agent model: {os.getenv('AZURE_AGENT_MODEL')}")
    print(f"Meta agent model: {os.getenv('AZURE_META_AGENT_MODEL')}")
    print(f"Experiment name: {args.expr_name}")

    # search
    SEARCHING_MODE = True
    print("=============Searching=================")
    search(args)

    # evaluate
    SEARCHING_MODE = False
    print("=============Evaluating=================")
    evaluate(args)
