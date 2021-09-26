"""
Title: Large-scale multi-label text classification
Author: [Sayak Paul](https://twitter.com/RisingSayak), [Soumik Rakshit](https://github.com/soumik12345)
Date created: 2020/09/25
Last modified: 2020/09/26
Description: Implementing a large-scale multi-label text classification model.
"""
"""
## Introduction

In this example, we will build a multi-label text classifier to predict the subject areas
of arXiv papers from their abstract bodies. This type of classifier can be useful for
conference submission portals like [OpenReview](https://openreview.net/). Given a paper
abstract, the portal could provide suggestions on which areas the underlying paper would
best belong to.

The dataset was collected using the
[`arXiv` Python library](https://github.com/lukasschwab/arxiv.py)
that provides a wrapper around the
[original arXiv API](http://arxiv.org/help/api/index). To know more, please refer to
[this notebook](https://github.com/soumik12345/multi-label-text-classification/blob/master/arxiv_scrape.ipynb).
Additionally, you can also find the dataset on
[Kaggle](https://www.kaggle.com/spsayakpaul/arxiv-paper-abstracts).
"""

"""
## Imports
"""

from tensorflow.keras import layers
from tensorflow import keras
import tensorflow as tf

from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from ast import literal_eval

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

"""
## Read data and perform basic EDA

In this section, we first load the dataset into a `pandas` dataframe and then perform
some basic exploratory data analysis (EDA).
"""

arxiv_data = pd.read_csv(
    "https://github.com/soumik12345/multi-label-text-classification/releases/download/v0.2/arxiv_data.csv"
)
arxiv_data.head()

"""
Our text features are present in the `summaries` column and their corresponding labels
are in `terms`. As we can notice there are multiple categories associated with a
particular entry.
"""

print(f"There are {len(arxiv_data)} rows in the dataset.")

"""
Real-world data is noisy. One of the most commonly observed such noise is data
duplication. Here we notice that our initial dataset has got about 13k duplicate entries.

"""

total_duplicate_titles = sum(arxiv_data["titles"].duplicated())
print(f"There are {total_duplicate_titles} duplicate titles.")

"""
Before proceeding further we first drop these entries. 
"""

arxiv_data = arxiv_data[~arxiv_data["titles"].duplicated()]
print(f"There are {len(arxiv_data)} rows in the deduplicated dataset.")

# There are some terms with occurrence as low as 1.
print(sum(arxiv_data["terms"].value_counts() == 1))

# How many unique terms?
print(arxiv_data["terms"].nunique())

"""
As observed above, out of 3157 unique combinations of `terms`, 2321 entries have the
lowest occurrence. To prepare our train, validation, and test sets with
[stratification](https://en.wikipedia.org/wiki/Stratified_sampling), we need to drop
these terms. 
"""

# Filtering the rare terms.
arxiv_data_filtered = arxiv_data.groupby("terms").filter(lambda x: len(x) > 1)
arxiv_data_filtered.shape

"""
## Convert the string labels to list of strings

The initial labels are represented as raw strings. Here we make them `List[str]` for a
more compact representation.
"""

arxiv_data_filtered["terms"] = arxiv_data_filtered["terms"].apply(
    lambda x: literal_eval(x)
)
arxiv_data_filtered["terms"].values[:5]

"""
## Stratified splits because of class imbalance

The dataset has a
[class imbalance problem](https://developers.google.com/machine-learning/glossary/#class-imbalanced-dataset).
So, to have a fair evaluation result, we need to ensure the datasets are sampled with
stratification. To know more about different strategies to deal with the class imbalance
problem, you can follow
[this tutorial](https://www.tensorflow.org/tutorials/structured_data/imbalanced_data). 
For an end-to-end demonstration of classification with imbablanced data, refer to 
[Imbalanced classification: credit card fraud detection](https://keras.io/examples/structured_data/imbalanced_classification/).
"""

test_split = 0.1

# Initial train and test split.
train_df, test_df = train_test_split(
    arxiv_data_filtered,
    test_size=test_split,
    stratify=arxiv_data_filtered["terms"].values,
)

# Splitting the test set further into validation
# and new test sets.
val_df = test_df.sample(frac=0.5)
test_df.drop(val_df.index, inplace=True)

print(f"Number of rows in training set: {len(train_df)}")
print(f"Number of rows in validation set: {len(val_df)}")
print(f"Number of rows in test set: {len(test_df)}")

"""
## Multi-label binarization

Now we preprocess our labels using
[`MultiLabelBinarizer`](http://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.MultiLabelBinarizer.html). 
"""

mlb = MultiLabelBinarizer()
mlb.fit_transform(train_df["terms"])
mlb.classes_

"""
`MultiLabelBinarizer`separates out the individual unique classes available from the label
pool and then uses this information to represent a given label set with 0's and 1's.
Below is an example.
"""

sample_label = train_df["terms"].iloc[0]
print(f"Original label: {sample_label}")

label_binarized = mlb.transform([sample_label])
print(f"Label-binarized representation: {label_binarized}")

"""
## Data preprocessing and `tf.data.Dataset` objects

We first get percentile estimates of the sequence lengths. The purpose will be clear in a
moment.
"""

train_df["summaries"].apply(lambda x: len(x.split(" "))).describe()

"""
Notice that 50% of the abstracts have a length of 154 (you may get a different number
based on the split). So, any number near that is a good enough approximate for the
maximum sequence length.

Now, we write utilities to prepare our datasets that would go straight to the text
classifier model.
"""

max_seqlen = 150
batch_size = 128
padding_token = "<pad>"
auto = tf.data.AUTOTUNE


def unify_text_length(text, label):
    # Split the given abstract and calculate its length.
    word_splits = tf.strings.split(text, sep=" ")
    sequence_length = tf.shape(word_splits)[0]

    # Calculate the padding amount.
    padding_amount = max_seqlen - sequence_length

    # Check if we need to pad or truncate.
    if padding_amount > 0:
        unified_text = tf.pad([text], [[0, padding_amount]], constant_values="<pad>")
        unified_text = tf.strings.reduce_join(unified_text, separator="")
    else:
        unified_text = tf.strings.reduce_join(word_splits[:max_seqlen], separator=" ")

    # The expansion is needed for subsequent vectorization.
    return tf.expand_dims(unified_text, -1), label


def make_dataset(dataframe, is_train=True):
    label_binarized = mlb.transform(dataframe["terms"].values)
    dataset = tf.data.Dataset.from_tensor_slices(
        (dataframe["summaries"].values, label_binarized)
    )
    dataset = dataset.shuffle(batch_size * 10) if is_train else dataset
    dataset = dataset.map(unify_text_length, num_parallel_calls=auto).cache()
    return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)


"""
Now we can prepare the `tf.data.Dataset` objects. 
"""

train_dataset = make_dataset(train_df, is_train=True)
validation_dataset = make_dataset(val_df, is_train=False)
test_dataset = make_dataset(test_df, is_train=False)

"""
## Dataset preview
"""

text_batch, label_batch = next(iter(train_dataset))

for i, text in enumerate(text_batch[:5]):
    label = label_batch[i].numpy()[None, ...]
    print(f"Abstract: {text[0]}")
    print(f"Label(s): {mlb.inverse_transform(label)[0]}")
    print(" ")

"""
## Vectorization

Before we feed the data to our model we need to represent them as numbers. For that
purpose, we will use the
[`TextVectorization` layer](https://keras.io/api/layers/preprocessing_layers/text/text_vectorization).
It can operate as a part of your main model so that the model is excluded from the core
preprocessing logic. This greatly reduces the chances of training and serving skew.

"""

"""
We now create our text classifier model with the `TextVectorization` layer present
inside it. 
"""

"""
## Create model with `TextVectorization`

A batch of raw text will first go through the `TextVectorization` layer and it will
generate their integer representations. Internally, the `TextVectorization` layer will
first create bi-grams out of the sequences and then represent them using
[TF-IDF](https://wikipedia.org/wiki/Tf%E2%80%93idf). The output representations will then
be passed to the shallow model responsible for text classification. 

To know more about other possible configurations with `TextVectorizer`, please consult
the 
[official documentation](https://keras.io/api/layers/preprocessing_layers/text/text_vectorization).

"""

text_vectorizer = layers.TextVectorization(
    max_tokens=20000, ngrams=2, output_mode="tf_idf"
)

# `TextVectorization` needs to be adapted as per the vocabulary from our
# training set.
with tf.device("/CPU:0"):
    text_vectorizer.adapt(train_dataset.map(lambda text, label: text))


def make_model():
    shallow_mlp_model = keras.Sequential(
        [
            text_vectorizer,
            layers.Dense(512, activation="relu"),
            layers.Dense(256, activation="relu"),
            layers.Dense(len(mlb.classes_), activation="sigmoid"),
        ]
    )
    return shallow_mlp_model


"""
Let's take a quick look at the summary of our shallow model.
"""

shallow_mlp_model = make_model()
shallow_mlp_model.summary()

"""
## Train the model

We will train our model using the binary cross-entropy loss. This is because the labels
are not disjoint. For a given abstract, we may have multiple categories. So, we will
divide the prediction task into a series of multiple binary classification problems. This
is also why we kept the activation function of the classification layer in our model to
sigmoid. Researchers have used other combinations of loss function and activation
function as well. For example, in
[Exploring the Limits of Weakly Supervised Pretraining](https://arxiv.org/abs/1805.00932),
Mahajan et al. used the softmax activation function and cross-entropy loss to train
their models.
"""

epochs = 20

shallow_mlp_model.compile(
    loss="binary_crossentropy", optimizer="adam", metrics=["categorical_accuracy"]
)

history = shallow_mlp_model.fit(
    train_dataset, validation_data=validation_dataset, epochs=epochs
)


def plot_result(item):
    plt.plot(history.history[item], label=item)
    plt.plot(history.history["val_" + item], label="val_" + item)
    plt.xlabel("Epochs")
    plt.ylabel(item)
    plt.title("Train and Validation {} Over Epochs".format(item), fontsize=14)
    plt.legend()
    plt.grid()
    plt.show()


plot_result("loss")
plot_result("categorical_accuracy")

"""
While training, we notice an initial sharp fall in the loss followed by a gradual decay.
"""

"""
### Evaluate the model
"""

_, categorical_acc = shallow_mlp_model.evaluate(test_dataset)
print(f"Categorical accuracy on the test set: {round(categorical_acc * 100, 2)}%.")

"""
The trained model gives us a validation accuracy of ~70%.
"""

"""
## Inference
"""

text_batch, label_batch = next(iter(test_dataset))
predicted_probabilities = shallow_mlp_model.predict(text_batch)

for i, text in enumerate(text_batch[:5]):
    label = label_batch[i].numpy()[None, ...]
    print(f"Abstract: {text[0]}")
    print(f"Label(s): {mlb.inverse_transform(label)[0]}")
    predicted_proba = [proba for proba in predicted_probabilities[i]]
    top_3_labels = [
        x
        for _, x in sorted(
            zip(predicted_probabilities[i], mlb.classes_),
            key=lambda pair: pair[0],
            reverse=True,
        )
    ][:3]
    print(f"Predicted Label(s): ({', '.join([label for label in top_3_labels])})")
    print(" ")

"""
The prediction results are not that great but not below the par for a simple model like
ours. We can improve this performance with models that consider word order like LSTM or
even those that use Transformers ([Vaswani et al.](https://arxiv.org/abs/1706.03762)).
"""
