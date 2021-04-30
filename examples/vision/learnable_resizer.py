"""
Title: Learning to Resize in Computer Vision
Author: [Sayak Paul](https://twitter.com/RisingSayak)
Date created: 2021/04/30
Last modified: 2021/04/30
Description: How to optimally learn representations of images for a given resolution.
"""
"""
It is a common belief that if we constrain vision models to perceive things as humans do,
their performance can be improved. For example, in [this
work](https://arxiv.org/abs/1811.12231), Geirhos et. al showed that the vision models
pre-trained on the ImageNet-1k dataset are biased toward texture whereas human beings
mostly use the shape descriptor to develop a common perception. But does this belief
always apply especially when it comes to improving the performance of vision models? 

It turns out it may not always be the case. When training vision models, it is common to
resize images to a lower dimension ((224x224), (299x299), etc.) to allow mini-batch
learning and also to keep up the compute limitations.  We generally make use of image
resizing methods like **bilinear interpolation** for this step and the resized images do
not lose much of their perceptual character to the human eyes. In [Learning to Resize
Images for Computer Vision Tasks](https://arxiv.org/abs/2103.09950v1), Talebi et. al show
that if we try to optimize the perceptual quality of the images for the vision models
rather than the human eyes, their performance can further be improved. They investigate
the following question: 

**For a given image resolution and a model, how to best resize the given images?**

As shown in the paper, this idea helps to consistently improve the performance of the
common vision models (pre-trained on ImageNet-1k) like DenseNet121, ResNet50,
MobileNetV2, and EfficientNets. In this example, we will implement the learnable image
resizing module as proposed in the paper and demonstrate that on the
[Cast-Vs-Dogs dataset](https://www.microsoft.com/en-us/download/details.aspx?id=54765)
using the [DenseNet121](https://arxiv.org/abs/1608.06993) model. 

This example requires TensorFlow 2.4 or higher.
"""

"""
## Setup
"""

from tensorflow.keras import layers
from tensorflow import keras
import tensorflow as tf

import tensorflow_datasets as tfds
tfds.disable_progress_bar()

import matplotlib.pyplot as plt
import numpy as np

"""
## Define hyperparameters
"""

"""
In order to facilitate mini-batch learning, we need to have a fixed shape for the images
inside a given batch. This is why an initial resizing is required. We first resize all
the images to (300x300) shape and then learn their optimal representation for the
(224x224) resolution. 
"""

INP_DIM = (300, 300)
TARGET_DIM = (224, 224)
INTERPOLATION = "bilinear"

AUTO = tf.data.AUTOTUNE
BATCH_SIZE = 64
EPOCHS = 5
ALPHA = 0.2

"""
For this example, we will use the bilinear interpolation but the learnable image resizer
module is not dependent on any specific interpolation method. We can use other ones (such
as bicubic) as well. 
"""

"""
## Load and prepare the dataset

For this example, we will only use 40% of the total training dataset.
"""

train_ds, validation_ds = tfds.load(
    "cats_vs_dogs",
    # Reserve 10% for validation
    split=["train[:40%]", "train[40%:50%]"],
    as_supervised=True,
)


def preprocess_dataset(image, label):
    image = tf.image.resize(image, (INP_DIM[0], INP_DIM[1]))
    label = tf.one_hot(label, depth=2)
    return (image, label)


train_ds = (
    train_ds.shuffle(BATCH_SIZE * 100)
    .map(preprocess_dataset, num_parallel_calls=AUTO)
    .batch(BATCH_SIZE)
    .prefetch(AUTO)
)
validation_ds = (
    validation_ds.map(preprocess_dataset, num_parallel_calls=AUTO)
    .batch(BATCH_SIZE)
    .prefetch(AUTO)
)

"""
## Define the learnable resizer utilities

The figure below (courtesy of the original paper) presents the structure of the learnable
resizing module:

![](https://i.ibb.co/gJYtSs0/image.png)
"""


def conv_block(x, filters, kernel_size, strides, activation=layers.LeakyReLU(ALPHA)):
    x = layers.Conv2D(filters, kernel_size, strides, padding="same", use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    if activation:
        x = activation(x)
    return x


def res_block(x):
    inputs = x
    x = conv_block(x, 16, 3, 1)
    x = conv_block(x, 16, 3, 1, activation=None)
    return layers.Add()([inputs, x])


def learnable_resizer(
    inputs, filters=16, num_res_blocks=1, interpolation=INTERPOLATION
):

    # We first do a naive resizing.
    naive_resize = layers.experimental.preprocessing.Resizing(
        *TARGET_DIM, interpolation=interpolation
    )(inputs)

    # First conv block without Batch Norm.
    x = layers.Conv2D(filters=filters, kernel_size=7, strides=1, padding="same")(inputs)
    x = layers.LeakyReLU(ALPHA)(x)

    # Second conv block with Batch Norm.
    x = layers.Conv2D(filters=filters, kernel_size=1, strides=1, padding="same")(x)
    x = layers.LeakyReLU(ALPHA)(x)
    x = layers.BatchNormalization()(x)

    # Intermediate resizing as bottleneck.
    bottleneck = layers.experimental.preprocessing.Resizing(
        *TARGET_DIM, interpolation=interpolation
    )(x)

    # Residual passes.
    for _ in range(num_res_blocks):
        x = res_block(bottleneck)

    # Projection.
    x = layers.Conv2D(
        filters=filters, kernel_size=3, strides=1, padding="same", use_bias=False
    )(x)
    x = layers.BatchNormalization()(x)

    # Skip connection
    x = layers.Add()([bottleneck, x])

    # Final resized image
    x = layers.Conv2D(filters=3, kernel_size=7, strides=1, padding="same")(x)
    final_resize = layers.Add()([naive_resize, x])

    return final_resize


"""
## Visualize the outputs of the learnable resizing module

Here, we visualize how the resized images would look like after being passed through the
random weights of the resizer. 
"""

sample_images, _ = next(iter(train_ds))

plt.figure(figsize=(10, 10))
for i, image in enumerate(sample_images[:9]):
    ax = plt.subplot(3, 3, i + 1)
    image = tf.image.convert_image_dtype(image, tf.float32)
    resized_image = learnable_resizer(image[None, ...])
    plt.imshow(resized_image.numpy().squeeze())
    plt.axis("off")

"""
## Model building utility
"""


def get_model():
    backbone = tf.keras.applications.DenseNet121(
        weights=None, include_top=True, classes=2
    )
    backbone.trainable = True

    inputs = layers.Input((INP_DIM[0], INP_DIM[1], 3))
    x = layers.experimental.preprocessing.Rescaling(scale=1.0 / 255)(inputs)
    x = learnable_resizer(x)
    outputs = backbone(x)

    return tf.keras.Model(inputs, outputs)


"""
## Compile and train our model with learnable resizer
"""

model = get_model()
model.compile(
    loss=keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
    optimizer="sgd",
    metrics=["accuracy"],
)
model.fit(train_ds, validation_data=validation_ds, epochs=EPOCHS)

"""
## Visualize the outputs of the trained visualizer
"""

learned_resizer = tf.keras.Model(model.input, model.layers[-2].output)

plt.figure(figsize=(10, 10))
for i, image in enumerate(sample_images[:9]):
    ax = plt.subplot(3, 3, i + 1)
    image = tf.image.convert_image_dtype(image, tf.float32)
    resized_image = learned_resizer(image[None, ...])
    plt.imshow(resized_image.numpy().squeeze())
    plt.axis("off")

"""
As we can see the visuals of the images have improved with training. Additionally, you
can find this repository that shows the benefits of using the resizing module. Below is a
comparison:

|           Model           	| Number of  parameters (Million) 	| Top-1 accuracy 	|
|:-------------------------:	|:-------------------------------:	|:--------------:	|
|   With learnable resizer  	|             7.051717            	|      52.02     	|
| Without learnable resizer 	|             7.039554            	|      50.3      	|

Note the above-reported models were trained for 10 epochs on 90% of the training set of
Cats-vs-Dogs unlike this example. Also, note that the increase in the number of
parameters due to the resizing module is very negligible. You can reproduce these results
from [this repository](https://github.com/sayakpaul/Learnable-Image-Resizing). To ensure
that the improvement in the performance is not due to stochasticity, the models were
trained using the same initial random weights. 
"""

"""
## Notes

* To impose shape bias inside the vision models, Geirhos et. al trained them with a
combination of natural and stylized images. It might be interesting to investigate if
this learnable resizing module could achieve something similar as the outputs seem to
discard the texture information. 
* Through a set of experiments, the authors also verify if the performance improvement is
***not*** solely due to the increase in the number of model parameters. You are
encouraged to check those out in the
[original paper](https://arxiv.org/abs/2103.09950v1). 
"""
