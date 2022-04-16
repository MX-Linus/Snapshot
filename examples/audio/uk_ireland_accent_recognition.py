"""
Title: UK & Ireland Accent Recognition Using Transfer Learning
Author: [Fadi Badine](https://twitter.com/fadibadine)
Date created: 16/04/2022
Last modified: 16/04/2022
Description: This notebook trains a model to classify UK & Ireland accents using feature extraction from Yamnet.
"""

"""
# Prerequisits

We need to install TensorFlow IO that we use to resample audio files to 16 kHz as
required by Yamnet model
"""

"""shell
pip install -U -q tensorflow_io
"""

"""
# Configuration
"""

SEED = 1337
EPOCHS = 100
BATCH_SIZE = 64
VALIDATION_RATIO = 0.1
MODEL_NAME = "uk_irish_accent_recognition"

# Location where the dataset will be downloaded.
# By default (None), keras.utils.get_file will use /root/.keras/ as the CACHE_DIR
CACHE_DIR = None

# The location of the dataset
URL_PATH = "https://www.openslr.org/resources/83/"

# List of datasets compressed files that contain the audio files
zip_files = {
    0: "irish_english_male.zip",
    1: "midlands_english_female.zip",
    2: "midlands_english_male.zip",
    3: "northern_english_female.zip",
    4: "northern_english_male.zip",
    5: "scottish_english_female.zip",
    6: "scottish_english_male.zip",
    7: "southern_english_female.zip",
    8: "southern_english_male.zip",
    9: "welsh_english_female.zip",
    10: "welsh_english_male.zip",
}

# We see that there are 2 compressed files for each accent (except Irish):
# - One for male speakers
# - One for female speakers
# However, we will using a gender agnostic dataset.

# List of gender agnostic categories
gender_agnostic_categories = [
    "ir",  # Irish
    "mi",  # Midlands
    "no",  # Northern
    "sc",  # Scottish
    "so",  # Southern
    "we",  # Welsh
]

class_names = [
    "Irish",
    "Midlands",
    "Northern",
    "Scottish",
    "Southern",
    "Welsh",
    "Not a speech",
]

import os
import io
import csv
import random
import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_hub as hub
import tensorflow_io as tfio

from tensorflow import keras

import matplotlib.pyplot as plt
import seaborn as sns

from scipy import stats
from IPython.display import Audio

print(f"TensorFlow: {tf.__version__}")
print(f"TensorFlow Hub: {hub.__version__}")
print(f"TensorFlow IO: {tfio.__version__}")


def d_prime(auc):
    standard_normal = stats.norm()
    d_prime = standard_normal.ppf(auc) * np.sqrt(2.0)
    return d_prime


def reset_random_seed(seed=1337):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


reset_random_seed(SEED)

# Where to download the dataset
DATASET_DESTINATION = os.path.join(
    CACHE_DIR if CACHE_DIR else "/root/.keras/", "datasets"
)

"""
# Yamnet Model

Yamnet is an audio event classifier trained on the AudioSet dataset to predict audio
events from the AudioSet ontology. It is available on TensorFlow Hub.

Yamnet accepts a 1-D tensor of audio samples with a sample rate of 16 kHz.
As output, the model returns a 3-tuple:
- scores of shape (N, 521) representing the scores of the 521 classes
- embeddings of shape (N, 1024)
- log_mel spectrogram representing the log-mel spectrogram of the entire audio frame

We will use the embeddings, which are the features extracted from the audio samples, as the input to our dense model.

For more detailed information about Yamnet, please refer to its [TensorFlow Hub](https://tfhub.dev/google/yamnet/1) page.
"""

yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")

"""
# Dataset

The dataset used is the **[Open-source Multi-speaker Corpora of the English Accents in
the British Isles](https://openslr.org/83/)** which consists of a total of **17,877 audio
files**.
"""

"""
## Dataset Info
@inproceedings{demirsahin-etal-2020-open,
title = {{Open-source Multi-speaker Corpora of the English Accents in the British Isles}},
author = {Demirsahin, Isin and Kjartansson, Oddur and Gutkin, Alexander and Rivera, Clara},
booktitle = {Proceedings of The 12th Language Resources and Evaluation Conference (LREC)},
    month = may,
    year = {2020},
    pages = {6532--6541},
    address = {Marseille, France},
    publisher = {European Language Resources Association (ELRA)},
    url = {https://www.aclweb.org/anthology/2020.lrec-1.804},
    ISBN = {979-10-95546-34-4},
  }
"""

"""
## Download Dataset
"""

# CSV file that contains information about the dataset. For each entry, we have:
# - ID
# - wav file name
# - transcript
line_index_file = keras.utils.get_file(
    fname="line_index_file", origin=URL_PATH + "line_index_all.csv"
)

# Download the list of compressed files that contains the audio wav files
for i in zip_files:
    fname = zip_files[i].split(".")[0]
    url = URL_PATH + zip_files[i]

    zip_file = keras.utils.get_file(fname=fname, origin=url, extract=True)
    os.remove(zip_file)

"""
## Dataframe
"""

"""
### Load & Preprocess

Of the 3 columns (ID, filename and transcript), we are only interested in the filename column in order to read the audio file.
We will ignore the other 2
"""

dataframe = pd.read_csv(
    line_index_file, names=["id", "filename", "transcript"], usecols=["filename"]
)
dataframe.head()

"""
Let's now preprocess the dataset by:

*   Adjusting the filename (removing a leading space & adding ".wav" extension to the
filename)
*   Creating a label using the first 2 characters of the filename which indicate the
accent
*   Shuffling the samples
"""

# The purpose of this function is to preprocess the dataframe by applying the following:
# - Cleaning the filename from a leading space
# - Generating a label column that is gender agnostic i.e.
#   welsh english male and welsh english female for example are both labeled as
#   welsh english
# - Add extension .wav to the filename
# - Shuffle samples
def preprocess_dataframe(dataframe):
    # Remove leading space in filename column
    dataframe["filename"] = dataframe.apply(lambda row: row["filename"].strip(), axis=1)

    # Create gender agnostic labels based on the filename first 2 letters
    dataframe["label"] = dataframe.apply(
        lambda row: gender_agnostic_categories.index(row["filename"][:2]), axis=1
    )

    # Add the file path to the name
    dataframe["filename"] = dataframe.apply(
        lambda row: os.path.join(DATASET_DESTINATION, row["filename"] + ".wav"), axis=1
    )

    # Shuffle the samples
    dataframe = dataframe.sample(frac=1, random_state=SEED).reset_index(drop=True)

    return dataframe


dataframe = preprocess_dataframe(dataframe)
dataframe.head()

"""
### Train & Validation Sets

Let's split the samples creating training and validation sets
"""

split = int(len(dataframe) * (1 - VALIDATION_RATIO))
train_df = dataframe[:split]
valid_df = dataframe[split:]

print(
    f"We have {train_df.shape[0]} training samples & {valid_df.shape[0]} validation ones"
)

"""
## TensorFlow Dataset

Next, we need to create a `tf.data` dataset.
This is done by creating a `dataframe_to_dataset` function that does the following:
*   Create a dataset using filenames and labels
*   Get the Yamnet embeddings by calling another function `filepath_to_embeddings`
*   Apply caching, reshuffling and setting batch size

The `filepath_to_embeddings` does the following:
*   Load audio file
*   Resample audio to 16 kHz
*   Generate scores and embeddings from Yamnet model
*   Since Yamnet generates multiple samples for each audio file, this function also duplicates the label for all the generated samples that have `score = 0` i.e. speech whereas sets the label for the others as 'other' indicating that this audio segment is not a speech and we won't label it as one of the accents.

"""

"""
The below **`load_16k_audio_file`** is copied from the following tutorial [Transfer
learning with YAMNet for environmental sound
classification](https://www.tensorflow.org/tutorials/audio/transfer_learning_audio)
"""


@tf.function
def load_16k_audio_wav(filename):
    # Read file content
    file_content = tf.io.read_file(filename)

    # Decode audio wave
    audio_wav, sample_rate = tf.audio.decode_wav(file_content, desired_channels=1)
    audio_wav = tf.squeeze(audio_wav, axis=-1)
    sample_rate = tf.cast(sample_rate, dtype=tf.int64)

    # Resample to 16k
    audio_wav = tfio.audio.resample(audio_wav, rate_in=sample_rate, rate_out=16000)

    return audio_wav


def filepath_to_embeddings(filename, label):
    # Load 16k audio wave
    audio_wav = load_16k_audio_wav(filename)

    # Get audio embeddings & scores.
    # The embeddings are the audio features extracted using transfer learning
    # while scores will be used to identify time slots that are not speech
    # which will then be gathered into a specific new category 'other'
    scores, embeddings, _ = yamnet_model(audio_wav)

    # Number of embeddings in order to know how many times to repeat the label
    embeddings_num = tf.shape(embeddings)[0]
    labels = tf.repeat(label, embeddings_num)

    # Change labels for time-slots that are not speech into a new category 'other'
    labels = tf.where(tf.argmax(scores, axis=1) == 0, label, len(class_names) - 1)

    # Using one-hot in order to use AUC
    return (embeddings, tf.one_hot(labels, len(class_names)))


def dataframe_to_dataset(dataframe, batch_size=64):
    dataset = tf.data.Dataset.from_tensor_slices(
        (dataframe["filename"], dataframe["label"])
    )

    dataset = dataset.map(lambda X, y: filepath_to_embeddings(X, y)).unbatch()

    return dataset.cache().batch(batch_size).prefetch(tf.data.AUTOTUNE)


train_ds = dataframe_to_dataset(train_df)
valid_ds = dataframe_to_dataset(valid_df)

"""
# Model

The dense model that we use consists of:
*   An input layer which is the embedding output of the Yamnet classifier
*   4 dense hidden layers and 4 dropout layers
*   An output dense layer

The model's hyperparameters were selected using
[KerasTuner](https://keras.io/keras_tuner/).
"""

keras.backend.clear_session()

"""
## Building & Compilation
"""


def build_and_compile_model():
    inputs = keras.layers.Input(shape=(1024), name="embedding")

    x = keras.layers.Dense(256, activation="relu", name="dense_1")(inputs)
    x = keras.layers.Dropout(0.15, name="dropout_1")(x)

    x = keras.layers.Dense(384, activation="relu", name="dense_2")(x)
    x = keras.layers.Dropout(0.2, name="dropout_2")(x)

    x = keras.layers.Dense(192, activation="relu", name="dense_3")(x)
    x = keras.layers.Dropout(0.25, name="dropout_3")(x)

    x = keras.layers.Dense(384, activation="relu", name="dense_4")(x)
    x = keras.layers.Dropout(0.2, name="dropout_4")(x)

    outputs = keras.layers.Dense(len(class_names), activation="softmax", name="ouput")(
        x
    )

    model = keras.Model(inputs=inputs, outputs=outputs, name="accent_recognition")

    auc = keras.metrics.AUC(name="auc")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1.9644e-5),
        loss=keras.losses.CategoricalCrossentropy(),
        metrics=["accuracy", auc],
    )

    return model


model = build_and_compile_model()
model.summary()

"""
## Class Weights Calculation

Since the dataset is quite unbalanced, we wil use class_weight during training.
Getting the class weights is a little tricky because even though we know the number of audio files for each class, it does not represent the number of samples for that class since Yamnet transforms each audio file into multiple audio samples of 0.96 seconds each.
So every audio file will be split into a number of samples that is proportional to its length.
Therefore, to get those weights, we have to calculate the number of samples for each class after preprocessing through Yamnet.
"""

class_counts = tf.zeros(shape=(len(class_names),), dtype=tf.int32)

for X, y in iter(train_ds):
    class_counts = class_counts + tf.math.bincount(
        tf.cast(tf.math.argmax(y, axis=1), tf.int32), minlength=len(class_names)
    )

class_weight = {
    i: tf.math.reduce_sum(class_counts).numpy() / class_counts[i].numpy()
    for i in range(len(class_counts))
}

print(class_weight)

"""
## Callbacks

A couple of Keras callbacks in order to:
*   Stop whenever the validation AUC stops improving
*   Save the best model
*   Call TensorBoard in order to later view the training and validation logs
"""

early_stopping_cb = keras.callbacks.EarlyStopping(
    monitor="val_auc", patience=10, restore_best_weights=True
)

model_checkpoint_cb = keras.callbacks.ModelCheckpoint(
    MODEL_NAME + ".h5", monitor="val_auc", save_best_only=True
)

tensorboard_cb = keras.callbacks.TensorBoard(
    os.path.join(os.curdir, "logs", model.name)
)

callbacks = [early_stopping_cb, model_checkpoint_cb, tensorboard_cb]

"""
## Training
"""

history = model.fit(
    train_ds,
    epochs=EPOCHS,
    validation_data=valid_ds,
    class_weight=class_weight,
    callbacks=callbacks,
    verbose=2,
)

"""
## Results
"""

"""
### TensorBoard
"""

"""
```
%reload_ext tensorboard

%tensorboard --logdir=./logs/ --port=6066
```
"""

"""
### Evaluation
"""

train_loss, train_acc, train_auc = model.evaluate(train_ds)
valid_loss, valid_acc, valid_auc = model.evaluate(valid_ds)

print(
    "train d-prime: {0:.3f}, validation d-prime: {1:.3f}".format(
        d_prime(train_auc), d_prime(valid_auc)
    )
)

"""
We can see that the model achieves the following results:

Results    | Training  | Validation
-----------|-----------|------------
Accuracy   | 54%       | 51%
AUC        | 0.9091    | 0.8910
d-prime    | 1.888     | 1.742

"""

"""
### Confusion Matrix

Let's now plot the confusion matrix for the validation dataset.
"""

# Create X and y tensors
X_valid = None
y_valid = None

for X, y in iter(valid_ds):
    if X_valid is None:
        X_valid = X.numpy()
        y_valid = y.numpy()
    else:
        X_valid = np.concatenate((X_valid, X.numpy()), axis=0)
        y_valid = np.concatenate((y_valid, y.numpy()), axis=0)

# Generate predictions
y_pred = model.predict(X_valid)

# Calculate confusion matrix
confusion_mtx = tf.math.confusion_matrix(
    np.argmax(y_valid, axis=1), np.argmax(y_pred, axis=1)
)

# Plot the confusion matrix
plt.figure(figsize=(10, 8))
sns.heatmap(
    confusion_mtx, xticklabels=class_names, yticklabels=class_names, annot=True, fmt="g"
)
plt.xlabel("Prediction")
plt.ylabel("Label")
plt.title("Validation Confusion Matrix")
plt.show()

"""
### Precision & Recall
"""

for i, label in enumerate(class_names):
    precision = confusion_mtx[i, i] / np.sum(confusion_mtx[:, i])
    recall = confusion_mtx[i, i] / np.sum(confusion_mtx[i, :])
    print(
        "{0:15} Precision:{1:.2f}%; Recall:{2:.2f}%".format(
            label, precision * 100, recall * 100
        )
    )

"""
# Inference
"""

"""
The below function `yamnet_class_names_from_csv` was copied and very slightly changed
from [Yamnet
Notebook](https://colab.research.google.com/github/tensorflow/hub/blob/master/examples/colab/yamnet.ipynb)
Notebook](https://colab.research.google.com/github/tensorflow/hub/blob/master/examples/colab/yamnet.ipynb)
"""


def yamnet_class_names_from_csv(yamnet_class_map_csv_text):
    """Returns list of class names corresponding to score vector."""
    yamnet_class_map_csv = io.StringIO(yamnet_class_map_csv_text)
    yamnet_class_names = [
        name for (class_index, mid, name) in csv.reader(yamnet_class_map_csv)
    ]
    yamnet_class_names = yamnet_class_names[1:]  # Skip CSV header
    return yamnet_class_names


yamnet_class_map_path = yamnet_model.class_map_path().numpy()
yamnet_class_names = yamnet_class_names_from_csv(
    tf.io.read_file(yamnet_class_map_path).numpy().decode("utf-8")
)


def calculate_number_of_non_speech(scores):
    number_of_non_speech = tf.math.reduce_sum(
        tf.where(tf.math.argmax(scores, axis=1, output_type=tf.int32) != 0, 1, 0)
    )

    return number_of_non_speech


def filename_to_predictions(filename):
    # Load 16k audio wave
    audio_wav = load_16k_audio_wav(filename)

    # Get audio embeddings & scores.
    scores, embeddings, mel_spectrogram = yamnet_model(audio_wav)

    print(
        "Out of {} samples, {} are not speech".format(
            scores.shape[0], calculate_number_of_non_speech(scores)
        )
    )

    # Predict the output of the accent recognition model with embeddings as input
    predictions = model.predict(embeddings)

    return audio_wav, predictions, mel_spectrogram


"""
## Run a test

Let's check this example from [The Scottish Voice](https://www.thescottishvoice.org.uk/home/)

"""

filename = "audio-sample-Stuart"
url = "https://www.thescottishvoice.org.uk/files/cm/files/"

if os.path.exists(filename + ".wav") == False:
    print(f"Downloading {filename}.mp3 from {url}")
    command = f"wget {url}{filename}.mp3"
    os.system(command)

    print(f"Converting mp3 to wav and resampling to 16 kHZ")
    command = (
        f"ffmpeg -hide_banner -loglevel panic -y -i {filename}.mp3 -acodec "
        f"pcm_s16le -ac 1 -ar 16000 {filename}.wav"
    )
    os.system(command)

filename = filename + ".wav"


audio_wav, predictions, mel_spectrogram = filename_to_predictions(filename)

infered_class = class_names[predictions.mean(axis=0).argmax()]
print(f"The main accent is: {infered_class} English")

"""
## Results
"""

"""
### Listen to the uploaded audio
"""

Audio(audio_wav, rate=16000)

"""
### Wavelength, Spectrogram & Prediction
"""

"""
The below function was copied from [Yamnet](tinyurl.com/4a8xn7at) notebook and adjusted to our need
"""

plt.figure(figsize=(10, 6))

# Plot the waveform.
plt.subplot(3, 1, 1)
plt.plot(audio_wav)
plt.xlim([0, len(audio_wav)])

# Plot the log-mel spectrogram (returned by the model).
plt.subplot(3, 1, 2)
plt.imshow(
    mel_spectrogram.numpy().T, aspect="auto", interpolation="nearest", origin="lower"
)

# Plot and label the model output scores for the top-scoring classes.
mean_predictions = np.mean(predictions, axis=0)

top_class_indices = np.argsort(mean_predictions)[::-1]
plt.subplot(3, 1, 3)
plt.imshow(
    predictions[:, top_class_indices].T,
    aspect="auto",
    interpolation="nearest",
    cmap="gray_r",
)

# patch_padding = (PATCH_WINDOW_SECONDS / 2) / PATCH_HOP_SECONDS
# values from the model documentation
patch_padding = (0.025 / 2) / 0.01
plt.xlim([-patch_padding - 0.5, predictions.shape[0] + patch_padding - 0.5])
# Label the top_N classes.
yticks = range(0, len(class_names), 1)
plt.yticks(yticks, [class_names[top_class_indices[x]] for x in yticks])
_ = plt.ylim(-0.5 + np.array([len(class_names), 0]))
