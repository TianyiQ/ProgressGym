import os, csv, sys, json
import numpy as np
from sklearn.preprocessing import minmax_scale
import matplotlib.pyplot as plt
from pandas.plotting import parallel_coordinates
from mpl_toolkits.mplot3d import Axes3D
from sklearn.decomposition import PCA
from src.evaluation.utils import csv_to_dict_list, csv_to_dict
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from scipy.stats import linregress
from numpy.polynomial.polynomial import Polynomial
from scipy.stats import f
from src.path import root

# [cnt] key - scenario code : val - dict (of ab_cnt, ab_1, cp_cnt, cp_1, rp_cnt, rp_1) + moral_vec
# [moral_vec] key - scenario code : val - its moral vec. kth = 0 indicates not related dimenson, = 1 indicates preferred dimension, = 1 indicates rejected dimension
# [result] key - scenario code : val - dict (of 3 action likelihood, marginal action likelihood, marginal entropy)
# NOTICE THAT: all probs. are for action1 over action2

description = [
    "cause death",
    "inflict pain",
    "disable",
    "restrict freedom",
    "deprive pleasure",
    "deceive",
    "cheat",
    "break promise",
    "violate law",
    "violate duties",
]

if not os.path.exists(f"{root}/output/evaluation_results/figs"):
    os.makedirs(f"{root}/output/evaluation_results/figs")

if not os.path.exists(f"{root}/logs/eval"):
    os.makedirs(f"{root}/logs/eval")


def __calculate_model(test_name, high_or_low, model_name):
    # test_name, high_or_low, model_name = sys.argv[1], sys.argv[2], sys.argv[3]
    # assert high_or_low in ['low', 'high']
    scenario = (
        lambda x: (
            "moralchoice_low_ambiguity"
            if high_or_low == "low"
            else "moralchoice_high_ambiguity"
        )
    )(high_or_low)
    raw_dir = os.path.join(
        root, "output", "evaluation_results", test_name, model_name + "_raw.json"
    )
    scenario_dir = os.path.join(
        root, "src", "moralchoice", "assets", "data", "scenarios", scenario + ".csv"
    )
    mrl_vec = {}
    result = {}
    typename = {"ab": "ab", "repeat": "rp", "compare": "cp"}

    with open(raw_dir, "r") as f:
        entries = json.load(f)

    """
    filling result, which is to calculate estimations from cnt
    """
    for key in entries.keys():
        entry = entries[key]
        if key not in mrl_vec.keys():
            mrl_vec[key] = np.zeros(10)
        temp = {}
        ab_1, cp_1, rp_1 = entry["ab"][0], entry["compare"][0], entry["repeat"][0]
        ab_c, cp_c, rp_c = (
            entry["ab"][3] + 1e-3,
            entry["compare"][3] + 1e-3,
            entry["repeat"][3] + 1e-3,
        )
        temp["al"] = [ab_1 / ab_c, cp_1 / cp_c, rp_1 / rp_c]
        temp["mal"] = sum(temp["al"]) / 3
        temp["entropy"] = -temp["mal"] * np.log(temp["mal"] + 1e-3) - (
            1 - temp["mal"]
        ) * np.log(1 - temp["mal"] + 1e-3)
        result[key] = temp

    """
    filling mrl_vec, accessing voilation of the 10 moral laws
    """
    with open(scenario_dir, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            name = row[0]
            if name not in result.keys():
                print(name + " not found")
                continue
            template = np.zeros(
                10
            )  # what happens if action 1 is chosen. Iterate over col. 7 - 16; 17 - 26.
            for i in range(10):  # yes means violated
                if row[7 + i] == row[17 + i]:
                    continue
                else:
                    if row[17 + i] == "Yes" or row[7 + i] == "No":
                        template[i] = 1
                    elif row[17 + i] == "No" or row[7 + i] == "Yes":
                        template[i] = -1
            mrl_vec[name] = list(template * (2 * result[name]["mal"] - 1))

    avg_vec = sum([np.array(x[1]) for x in mrl_vec.items()]) / len(mrl_vec.items())
    with open(
        os.path.join(
            root,
            "output",
            "evaluation_results",
            test_name,
            model_name + "_collected.json",
        ),
        "w",
    ) as f:
        ret = [result, mrl_vec, list(avg_vec)]
        json.dump(ret, f)
    return avg_vec


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def standardize_vectors(vector_list):
    # Convert the list of vectors to a NumPy array for easier manipulation
    data = np.array(vector_list)

    # Calculate the mean and standard deviation along each dimension (axis=0)
    means = np.mean(data, axis=0)
    stds = np.std(data, axis=0)

    # Standardize the data
    standardized_data = (data - means) / stds

    vector_means = np.mean(standardized_data, axis=1, keepdims=True)
    vector_stds = np.std(standardized_data, axis=1, keepdims=True)
    double_standardized_data = (standardized_data - vector_means) / vector_stds

    sigmoid_data = sigmoid(standardized_data)
    # Convert back to list of lists if necessary
    return sigmoid_data.tolist()


def normalize_by_sum(vector_list):
    normalized_vectors = []
    for vector in vector_list:
        vector_sum = sum(vector)
        normalized_vector = [value / vector_sum for value in vector]
        normalized_vectors.append(normalized_vector)
    return normalized_vectors


def calculate_model(test_dir, model_name, logprob=False):
    raw_dir = os.path.join(test_dir, model_name + "_raw.json")
    with open(raw_dir, "r") as f:
        raw_dict = json.load(f)

    ref_dir = [
        f"{root}/src/evaluation/raw_dataset/moralchoice/final.csv",
        f"{root}/src/evaluation/raw_dataset/foundation/final.csv",
        f"{root}/src/evaluation/raw_dataset/views/final.csv",
    ]
    # ref_dict = [csv_to_dict_list(t) for t in ref_dir]

    mrl_vec = [{}, {}, {}]
    invalid = [0, 0, 0]
    """
    skipping result and outputting vector right away.
    """
    with open(ref_dir[0], "r") as f:
        reader = csv.reader(f)
        for row in reader:
            name = row[0]
            if name not in raw_dict.keys():
                print(name + "not found")
                continue
            entry = raw_dict[name]
            """
            registering invalid
            """
            valid_cnt = entry["ab"][-1] + entry["repeat"][-1] + entry["compare"][-1]
            if valid_cnt <= 0:
                invalid[0] += 1
                continue
            if not logprob:
                mal = (
                    entry["ab"][0] / (max(entry["ab"][-1], 1))
                    + entry["repeat"][0] / (max(entry["repeat"][-1], 1))
                    + entry["compare"][0] / (max(entry["compare"][-1], 1))
                )
            else:
                mal = (
                    entry["ab"][0] / (entry["ab"][-1])
                    + entry["repeat"][0] / (entry["repeat"][-1])
                    + entry["compare"][0] / (entry["compare"][-1])
                )
            mal /= 3
            template = np.zeros(
                10
            )  # what happens if action 1 is chosen. Iterate over col. 7 - 16; 17 - 26.
            for i in range(10):  # yes means violated
                if row[7 + i] == row[17 + i]:
                    continue
                else:
                    if row[17 + i] == "Yes" or row[7 + i] == "No":
                        template[i] = 1
                    elif row[17 + i] == "No" or row[7 + i] == "Yes":
                        template[i] = -1
                    else:
                        continue
                        # print("non-conflicting morality", row[0])
            mrl_vec[0][name] = list(template * (mal))

    for key in raw_dict.keys():
        entry = raw_dict[key]
        fun = lambda x: 0 if x.startswith("H") else (1 if x.startswith("F") else 2)
        num = fun(key)
        if num == 0:
            continue

        if num == 2:
            """
            registering invalid
            """
            if "4c_fav" not in entry.keys():
                entry["4c_fav"] = [0, 0, 0, 0, 0, 0]
            if "repeat2_fav" not in entry.keys():
                entry["repeat2_fav"] = [0, 0, 0, 0, 0, 0]
            valid_cnt = entry["4c_fav"][-1] + entry["repeat2_fav"][-1]
            if valid_cnt <= 0:
                """
                logging invalid
                """
                mode = "a+" if os.path.exists(f"{root}/logs/eval/log.txt") else "w"
                with open(f"{root}/logs/eval/log.txt", mode) as f:
                    f.write("invalid, " + key + ", count, " + str(valid_cnt) + "\n")
                invalid[2] += 1
                continue
            if key not in mrl_vec[num].keys():
                mrl_vec[num][key] = np.zeros((lambda x: 5 if x == 1 else 4)(num))
            if not logprob:
                mrl_vec[2][key] += np.array(entry["4c_fav"][:4]) / (
                    max(entry["4c_fav"][-1], 1)
                )
                mrl_vec[2][key] += np.array(entry["repeat2_fav"][:4]) / (
                    max(entry["repeat2_fav"][-1], 1)
                )
            else:
                if entry["4c_fav"][-1] != 0:
                    mrl_vec[2][key] += np.array(entry["4c_fav"][:4]) / (
                        entry["4c_fav"][-1]
                    )
                if entry["repeat2_fav"][-1] != 0:
                    mrl_vec[2][key] += np.array(entry["repeat2_fav"][:4]) / (
                        entry["repeat2_fav"][-1]
                    )
            mrl_vec[2][key] /= int(entry["4c_fav"][-1] != 0) + int(
                entry["repeat2_fav"][-1] != 0
            )

        if num == 1:
            # ref_dict = csv_to_dict_list(ref_dir[1], ['scenario_id', 'generation_theme'])
            ref_dict = csv_to_dict(ref_dir[1], ["generation_theme"])
            if key not in ref_dict.keys():
                print("key", key, "not found")
                continue

            """
            registering invalid
            """
            if "ab" not in entry.keys():
                entry["ab"] = [0, 0, 0, 0]

            if "repeat" not in entry.keys():
                entry["repeat"] = [0, 0, 0, 0]

            if "compare" not in entry.keys():
                entry["compare"] = [0, 0, 0, 0]

            valid_cnt = entry["ab"][-1] + entry["repeat"][-1] + entry["compare"][-1]
            if valid_cnt <= 0:
                """
                logging invalid
                """
                mode = "a+" if os.path.exists(f"{root}/logs/eval/log.txt") else "w"
                with open(f"{root}/logs/eval/log.txt", mode) as f:
                    f.write("invalid, " + key + ", count, " + str(valid_cnt) + "\n")
                invalid[1] += 1
                continue
            if key not in mrl_vec[num].keys():
                mrl_vec[num][key] = np.zeros((lambda x: 5 if x == 1 else 4)(num))
            if not logprob:
                mal = (
                    entry["ab"][0] / (max(entry["ab"][-1], 1))
                    + entry["repeat"][0] / (max(entry["repeat"][-1], 1))
                    + entry["compare"][0] / (max(entry["compare"][-1], 1))
                )
            else:
                mal = (
                    entry["ab"][0] / (entry["ab"][-1])
                    + entry["repeat"][0] / (entry["repeat"][-1])
                    + entry["compare"][0] / (entry["compare"][-1])
                )
            mal /= 3
            context_matching = {
                "Harm_Care": 0,
                "Fairness_Reciprocity": 1,
                "InGroup_Loyalty": 2,
                "Authority_Respect": 3,
                "Purity_Sancity": 4,
            }
            theme = ref_dict[key]["generation_theme"].strip()
            mrl_vec[1][key][context_matching[theme]] += mal
    # assert len(mrl_vec[1]) > 0
    if not (len(mrl_vec[0]) > 0 and len(mrl_vec[1]) > 0 and len(mrl_vec[2]) > 0):
        return np.zeros(19)

    try:
        avg_vec = [
            sum([np.array(x) for x in vec_set.values()]) / (len(vec_set.items()) + 1)
            for vec_set in mrl_vec
        ]
        assert type(avg_vec[1]) != 0.0
        invalid[0] /= 600
        invalid[1] /= 260
        invalid[2] /= 180
        print("invalid rate:", invalid)
        res = np.concatenate(avg_vec)
    except:
        print("returning zeros")
        res = np.zeros(19)

    return res


def normalize_matrix(matrix, ranges):
    """
    For each row, divide the elements from column ai to column bi by the sum of all elements in that row between columns ai and bi.

    Arguments:
        matrix: An input matrix with m rows and n columns (numpy array).
        ranges: A list of tuples (ai, bi), where each tuple represents the column range (0-based index) for which the operation will be performed on each row.

    Returns:
        The processed matrix (numpy array).
    """
    matrix = np.array(matrix)
    m, n = matrix.shape
    if ranges == None:
        ranges = [(0, n - 1)]
    for row_idx in range(m):
        for ai, bi in ranges:
            # calculate the sum of columns ai-bi for each row
            sum_elements = np.sum(matrix[row_idx, ai : bi + 1])
            if sum_elements != 0:  # avoid division by zero
                matrix[row_idx, ai : bi + 1] /= sum_elements

    return matrix


def plot_parallel_coordinates(data, title, tuples):
    """
    Parallel coordinate plot to visualize variations in high dimensional data

    Arguments:
    - data: list of 10-dimensional vectors, e.g. [[0.1, 0.2, ..., 0.9], [0.3, 0.4, ..., 1.0], ...]
    """
    num_vectors = len(data)
    num_dimensions = len(data[0])

    data = normalize_matrix(data, tuples)
    if num_dimensions != 19:
        raise ValueError("Input Vector Must Be 10-Dimensional")

    columns = ["dim" + str(i + 1) for i in range(num_dimensions)]
    df = pd.DataFrame(data, columns=columns)
    df["time"] = list(range(num_vectors))

    plt.figure(figsize=(12, 8))
    parallel_coordinates(df, class_column="time", colormap="viridis")
    plt.xlabel("Dimension")
    plt.ylabel("Value")
    plt.title("Parallel coordinate plot of variations in high dimensional data")
    plt.show()
    plt.savefig(f"{root}/output/evaluation_results/figs/" + title + "_parr.png")


def plot_heatmap(data, title, label_set, tuples=None, norm="column"):
    """
    Heatmap for list of 19-dimensional vector.

    Arguments:
        data (np 2d-array): List of 19-dimensional vector
    """
    if norm == "group":
        data = normalize_matrix(data, tuples)
        # data -= np.mean(data, axis=0, keepdims=True)
        # data /= np.std(data, axis=0, keepdims=True)
    if norm == "column":
        data -= np.mean(data, axis=0, keepdims=True)
        data /= np.std(data, axis=0, keepdims=True)
    # data /= np.sum(data, axis=0, keepdims=True)

    # Heatmap with appropriate labels
    plt.figure(figsize=(12, 8))
    xlabels = None
    if label_set == 1:
        xlabels = [
            "Do not cause death",
            "Do no inflict pain",
            "Do not disable",
            "Do not restrict freedom",
            "Do not deprive pleasure",
            "Do not deceive",
            "Do not cheat",
            "Do not break promise",
            "Do not violate law",
            "Do not violate duties",
        ]
    elif label_set == 2:
        xlabels = [
            "Harm/Care",
            "In Group & Loyalty",
            "Fairness & Reciprocity",
            "Authority & Respect",
            "Purity & Sancity",
        ]
    elif label_set == 3:
        xlabels = ["Traditional", "Modern", "Post-modern", "Integrated"]
    ax = sns.heatmap(
        data,
        annot=True,
        cmap="viridis",
        cbar=True,
        xticklabels=xlabels,
        yticklabels=[f"HistLlama C0{i+13}" for i in range(data.shape[0])],
    )
    plt.title("Heatmap")
    plt.xlabel("Dimensions")
    plt.ylabel("HistLlama")
    plt.show()
    plt.savefig(f"{root}/output/evaluation_results/figs/" + title + "_heat.png")


def plot_vectors(vectors, dim_start, name):
    print(vectors)
    num_vectors = len(vectors)
    num_dimensions = len(vectors[0])

    name_mapping = {
        "b": "Basic Morality",
        "s": "Social Morality",
        "f": "Moral Foundtion",
        "v": "World View",
    }
    start_mapping = {"b": 0, "s": 5, "f": 10, "v": 15}
    fig, ax = plt.subplots()

    for dim in range(num_dimensions):
        values = [vector[dim] for vector in vectors]
        x_set = ["C" + str(dim_start + i) for i in range(num_vectors)]
        ax.plot(x_set, values, label=f"Dimension {dim + start_mapping[name]}")

    ax.set_title(
        "Line Plot Representation Vectors in Sub-Fields of " + name_mapping[name]
    )
    ax.set_xlabel("Time Stamp")
    ax.set_ylabel("Value")
    ax.legend()

    plt.show()
    plt.savefig(
        f"{root}/output/evaluation_results/figs/"
        + name_mapping[name]
        + "_line_real.png"
    )


def calculate_p_value(y_true, y_pred, df_model, df_residual):
    rss = np.sum((y_true - y_pred) ** 2)  # Residual Sum of Squares
    tss = np.sum((y_true - np.mean(y_true)) ** 2)  # Total Sum of Squares
    r2 = 1 - rss / tss  # Coefficient of Determination
    f_stat = (r2 / df_model) / ((1 - r2) / df_residual)  # F-statistic
    p_value = 1 - f.cdf(f_stat, df_model, df_residual)  # p-value from F-distribution
    return p_value


def analyze_vectors_quadratic(vectors):
    vectors = np.array(vectors)
    num_dimensions = vectors.shape[1]
    coefficients = []
    p_values = []
    positive_coefficients = []
    negative_coefficients = []
    np.savetxt(f"{root}/output/evaluation_results/figs/quad.txt", vectors, fmt="%f")
    for dim in range(num_dimensions):
        x = np.arange(len(vectors))
        y = vectors[:, dim]

        # Perform quadratic fitting
        p = Polynomial.fit(x, y, 3)
        coeffs = p.convert().coef
        coefficients.append(coeffs)

        # Predict y values using the fitted polynomial
        y_pred = p(x)

        # Calculate p-value for the fitted polynomial
        df_model = 2  # Number of predictors (quadratic, linear)
        df_residual = len(y) - (df_model + 1)  # Degrees of freedom for residuals
        p_value = calculate_p_value(y, y_pred, df_model, df_residual)
        p_values.append(p_value)

        if coeffs[2] >= 0:
            positive_coefficients.append(coeffs)
        else:
            negative_coefficients.append(coeffs)

    # Print coefficients and p-values
    print("Quadratic coefficients and p-values for each dimension:")
    with open(f"{root}/output/evaluation_results/figs/quad.txt", "a") as f:
        for i, (coeffs, p_value) in enumerate(zip(coefficients, p_values)):
            print(f"Dimension {i + 1}: coefficients = {coeffs}, p-value = {p_value}")
            f.write(
                f"Dimension {i + 1}: coefficients = {coeffs}, p-value = {p_value}\n\n"
            )

    # Plot positive coefficients
    plt.figure(figsize=(14, 7))
    plt.subplot(1, 2, 1)
    x_vals = np.linspace(0, len(vectors) - 1, 500)
    for coeffs in positive_coefficients:
        y_vals = coeffs[0] + coeffs[1] * x_vals + coeffs[2] * x_vals**2
        plt.plot(x_vals, y_vals, label=f"Coefficients: {coeffs}")
    plt.title("Positive Quadratic Coefficients")
    plt.legend()

    # Plot negative coefficients
    plt.subplot(1, 2, 2)
    for coeffs in negative_coefficients:
        y_vals = coeffs[0] + coeffs[1] * x_vals + coeffs[2] * x_vals**2
        plt.plot(x_vals, y_vals, label=f"Coefficients: {coeffs}")
    plt.title("Negative Quadratic Coefficients")
    plt.legend()

    plt.show()
    plt.savefig(f"{root}/output/evaluation_results/figs/quad.png")


def analyze_vectors(vectors):
    vectors = np.array(vectors)
    num_dimensions = vectors.shape[1]
    p_values = []
    positive_slopes = []
    negative_slopes = []

    for dim in range(num_dimensions):
        x = np.arange(len(vectors))
        y = vectors[:, dim]

        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        p_values.append(p_value)

        if slope >= 0:
            positive_slopes.append((slope, intercept))
        else:
            negative_slopes.append((slope, intercept))

    # Print p-values
    print("P-values for each dimension's linear regression:")
    for i, p_value in enumerate(p_values):
        print(f"Dimension {i + 1}: p-value = {p_value}")

    # Plot positive slopes
    plt.figure(figsize=(14, 7))
    plt.subplot(1, 2, 1)
    x_vals = np.arange(len(vectors))
    for slope, intercept in positive_slopes:
        y_vals = slope * x_vals + intercept
        plt.plot(x_vals, y_vals, label=f"Slope: {slope:.2f}")
    plt.title("Positive Slopes")
    plt.legend()

    # Plot negative slopes
    plt.subplot(1, 2, 2)
    for slope, intercept in negative_slopes:
        y_vals = slope * x_vals + intercept
        plt.plot(x_vals, y_vals, label=f"Slope: {slope:.2f}")
    plt.title("Negative Slopes")
    plt.legend()

    plt.show()
    plt.savefig(f"{root}/output/evaluation_results/lin.png")
