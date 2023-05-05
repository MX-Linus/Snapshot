"""
Title: Reproducibility in Keras Models
Author: [Frightera](https://github.com/Frightera)
Date created: 2023/05/05
Last modified: 2023/05/05
Description: Demonstration of random weight initialization and reproducibility in Keras models.
Accelerator: GPU
"""
"""
## Introduction
This example demonstrates how to control randomness in Keras models. Sometimes
you may want to reproduce the exact same results across runs, for experimentation
purposes or to debug a problem.

This tutorial applies to Keras 2.7 and higher.
"""

"""
## Setup
"""
import inspect
import json

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# Set the seed using keras.utils.set_random_seed. This will set:
# 1) `numpy` seed
# 2) `tensorflow` random seed
# 3) `python` random seed
keras.utils.set_random_seed(812)

# This will make TensorFlow ops as deterministic as possible.
tf.config.experimental.enable_op_determinism()

"""
## Weight initialization in Keras

Most of the layers in Keras have `kernel_initializer` and `bias_initializer`
parameters. These parameters allow you to specify the strategy used for
initializing the weights of layer variables. The following built-in initializers
are available as part of `tf.keras.initializers`:
"""
to_be_removed = ["Initializer", "Ones", "Zeros", "Identity"]
initializers_list = [
    string
    for string in dir(keras.initializers)
    if string[0].isupper() and string not in to_be_removed
]
print(initializers_list)

# Let's call each initializer two times and store the results in a dictionary.
results = {}

for initializer_name in initializers_list:
    print(f"Running {initializer_name} initializer")
    # Get the initializer object from the Keras initializers module
    initializer = getattr(keras.initializers, initializer_name)
    results[initializer_name] = []

    # Get the signature of the initializer
    initializer_signature = inspect.signature(initializer)

    for _ in range(2):
        # In order to get same results across multiple runs from an initializer,
        # you need to specify a seed value. Note that this is not related to
        # keras.utils.set_random_seed or tf.config.experimental.enable_op_determinism.
        # If you comment those lines, you will still get the same results.
        if "seed" in initializer_signature.parameters:
            result = initializer(seed=42)(shape=(3, 3))
        else:
            result = initializer()(shape=(3, 3))
        results[initializer_name].append(result)

# Check if the results are equal.
all_equal = True
for initializer_name, initializer_results in results.items():
    if not tf.experimental.numpy.allclose(
        initializer_results[0], initializer_results[1]
    ).numpy():
        all_equal = False
print(f"Are the results equal? {all_equal}")

"""
Now, let's inspect how two different initializer objects behave when they are
have the same seed value.
"""

# Setting the seed value for an initializer will cause two different objects
# to produce same results.
glorot_normal_1 = keras.initializers.GlorotNormal(seed=42)
glorot_normal_2 = keras.initializers.GlorotNormal(seed=42)

input_dim, neurons = 3, 5

# Call two different objects with same shape
result_1 = glorot_normal_1(shape=(input_dim, neurons))
result_2 = glorot_normal_2(shape=(input_dim, neurons))

# Check if the results are equal.
equal = tf.experimental.numpy.allclose(result_1, result_2).numpy()
print(f"Are the results equal? {equal}")

"""
If the seed value is not set (or different seed values are used), two different
objects will produce different results. Since the random seed is set at the beginning
of the notebook, the results will be same in the sequential runs. This is related
to the `keras.utils.set_random_seed`.
"""

glorot_normal_3 = keras.initializers.GlorotNormal()
glorot_normal_4 = keras.initializers.GlorotNormal()

# Let's call the initializer.
result_3 = glorot_normal_3(shape=(input_dim, neurons))

# Call the second initializer.
result_4 = glorot_normal_4(shape=(input_dim, neurons))

equal = tf.experimental.numpy.allclose(result_3, result_4).numpy()
print(f"Are the results equal? {equal}")

"""
`result_3` and `result_4` will be different, but when you run the notebook
again, `result_3` will have identical values to the ones in the previous run.
Same goes for `result_4`.
"""

"""
## Reproducibility in model training process
If you want to reproduce the results of a model training process, you need to
control the randomness sources during the training process. In order to show a
realistic example, this section utilizes `tf.data` using parallel map and shuffle
operations.

In order to start, let's create a simple function which returns the history
object of the Keras model.
"""


def train_model(train_data: tf.data.Dataset, test_data: tf.data.Dataset) -> dict:
    model = keras.Sequential(
        [
            layers.Conv2D(32, (3, 3), activation="relu", input_shape=(32, 32, 1)),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.2),
            layers.Conv2D(32, (3, 3), activation="relu"),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.2),
            layers.Conv2D(32, (3, 3), activation="relu"),
            layers.GlobalAveragePooling2D(),
            layers.Dense(64, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(10, activation="softmax"),
        ]
    )

    model.compile(
        optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"]
    )

    history = model.fit(train_data, epochs=5, validation_data=test_data)

    print(f"Model accuracy on test data: {model.evaluate(test_data)[1] * 100:.2f}%")

    return history.history


# Load the MNIST dataset
(train_images, train_labels), (
    test_images,
    test_labels,
) = keras.datasets.mnist.load_data()

# Construct tf.data.Dataset objects
train_ds = tf.data.Dataset.from_tensor_slices((train_images, train_labels))
test_ds = tf.data.Dataset.from_tensor_slices((test_images, test_labels))

"""
Remember we called `tf.config.experimental.enable_op_determinism()` at the
beginning of the function. This makes the `tf.data` operations deterministic.
However, making `tf.data` operations deterministic comes with a performance cost.
If you want to learn more about it, please check this [official guide](https://www.tensorflow.org/api_docs/python/tf/config/experimental/enable_op_determinism#determinism_and_tfdata).
"""


def prepare_dataset(image, label):
    # Cast and normalize the image
    image = tf.cast(image, tf.float32) / 255.0

    # Expand the channel dimension
    image = tf.expand_dims(image, axis=-1)

    # Resize the image
    image = tf.image.resize(image, (32, 32))

    return image, label


# Prepare the datasets, batch-map --> vectorized operations
train_data = (
    train_ds.shuffle(buffer_size=len(train_images))
    .batch(batch_size=64)
    .map(prepare_dataset, num_parallel_calls=tf.data.AUTOTUNE)
    .prefetch(buffer_size=tf.data.AUTOTUNE)
)

test_data = (
    test_ds.batch(batch_size=64)
    .map(prepare_dataset, num_parallel_calls=tf.data.AUTOTUNE)
    .prefetch(buffer_size=tf.data.AUTOTUNE)
)

"""
Train the model for the first time.
"""

history = train_model(train_data, test_data)

"""
Let's save our results into a json file, and restart the kernel. After
restarting the kernel, we should see the same results as the previous run,
this includes metrics and loss values both on the training and test data.
"""

# Save the history object into a json file
with open("history.json", "w") as fp:
    json.dump(history, fp)

"""
Do not run the cell above in order not to overwrite the results. Execute the
model training cell again and compare the results.
"""

with open("history.json", "r") as fp:
    history_loaded = json.load(fp)


"""
Compare the results one by one. You will see that they are equal.
"""
for key in history.keys():
    for i in range(len(history[key])):
        if not tf.experimental.numpy.allclose(
            history[key][i], history_loaded[key][i]
        ).numpy():
            print(f"{key} are not equal")

"""
## Conclusion
In this tutorial, you learned how to control the randomness sources in Keras and
TensorFlow. You also learned how to reproduce the results of a model training
process.

If you want to initialize the model with the same weights everytime, you need to
set `kernel_initializer` and `bias_initializer` parameters of the layers and provide
a `seed` value to the initializer.

There still may be some inconsistencies due to numerical error accumulation such
as using `recurrent_dropout` in RNN layers.

Reproducibility is subject to the environment. You'll get the same results if you
run the notebook or the code on the same machine with the same environment.
"""
