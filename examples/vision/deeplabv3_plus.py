"""
Title: Multiclass Semantic Segmentation using DeepLabV3+
Author: [Soumik Rakshit](http://github.com/soumik12345)
Date created: 2021/08/31
Last modified: 2021/09/1
Description: Implement DeepLabV3+ architecture for Multi-class Semantic Segmentation
"""
"""
## Introduction
"""

"""
Semantic segmentation with the goal to assign semantic labels to every pixel in an image
is one of the fundamental topics in computer vision. Deep convolutional neural networks
based on the Fully Convolutional Neural Network show striking improvement over systems
relying on hand-crafted features on benchmark tasks. In this example, we would implement
the **DeepLabV3+** model as proposed by the paper [Encoder-Decoder with Atrous Separable
Convolution for Semantic Image Segmentation](https://arxiv.org/pdf/1802.02611.pdf) for
multi-class semantic segmentation.
"""

"""
## Download Dataset
"""

import os
import cv2
import numpy as np
from glob import glob
import tensorflow as tf
from scipy.io import loadmat
import matplotlib.pyplot as plt

"""shell
!gdown https://drive.google.com/uc?id=1B9A9UCJYMwTL4oBEo4RZfbMZMaZhKJaz
!unzip -q instance-level-human-parsing.zip
"""

"""

"""

"""
## Building Tensorflow Dataset
"""

"""
For this example, we would be using 200 images from the instance-level human parsing
dataset to train our model.
"""

IMAGE_SIZE = 512
BATCH_SIZE = 4
NUM_CLASSES = 20
DATA_DIR = "./instance-level_human_parsing/instance-level_human_parsing/Training"
MAX_IMAGES = 200

train_images = sorted(glob(os.path.join(DATA_DIR, "Images/*")))[:MAX_IMAGES]
train_masks = sorted(glob(os.path.join(DATA_DIR, "Category_ids/*")))[:MAX_IMAGES]


def read_image(image_path, mask=False):
    image = tf.io.read_file(image_path)
    if mask:
        image = tf.image.decode_png(image, channels=1)
        image.set_shape([None, None, 1])
        image = tf.image.resize(images=image, size=[IMAGE_SIZE, IMAGE_SIZE])
        image = tf.cast(image, tf.float32)
    else:
        image = tf.image.decode_png(image, channels=3)
        image.set_shape([None, None, 3])
        image = tf.image.resize(images=image, size=[IMAGE_SIZE, IMAGE_SIZE])
        image = tf.cast(image, tf.float32) / 127.5 - 1
    return image


def load_data(image_list, mask_list):
    image = read_image(image_list)
    mask = read_image(mask_list, mask=True)
    return image, mask


def data_generator(image_list, mask_list):
    dataset = tf.data.Dataset.from_tensor_slices((image_list, mask_list))
    dataset = dataset.map(load_data, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(BATCH_SIZE, drop_remainder=True)
    dataset = dataset.repeat(1)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset


dataset = data_generator(train_images, train_masks)
dataset

"""
## Building DeepLabV3+ Model
"""

"""
DeepLabv3+ extends DeepLabv3 by employing a encoder-decoder structure. The encoder module
encodes multi-scale contextual information by applying atrous convolution at multiple
scales, while the simple yet effective decoder module refines the segmentation results
along object boundaries.

![](https://github.com/lattice-ai/DeepLabV3-Plus/raw/master/assets/deeplabv3_plus_diagram.png)
![](https://github.com/lattice-ai/DeepLabV3-Plus/raw/master/assets/deeplabv3_plus_diagram.png)


"""

"""
**Atrous Convolution:** With Atrous convolution, as we go deeper, we can keep the stride
constant but with larger field-of-view without increasing the number of parameters or the
amount of computation. And finally, we can have larger output feature map which is good
for semantic segmentation.

The reason for using **Atrous Spatial Pyramid Pooling** is that it is discovered as the
sampling rate becomes larger, the number of valid filter weights (i.e., the weights that
are applied to the valid feature region, instead of padded zeros) becomes smaller.
"""


def convolution_block(
    block_input,
    n_filters=256,
    kernel_size=3,
    dilation_rate=1,
    padding="same",
    use_bias=False,
):

    x = tf.keras.layers.Conv2D(
        n_filters,
        kernel_size=1,
        dilation_rate=1,
        padding="same",
        use_bias=use_bias,
        kernel_initializer=tf.keras.initializers.HeNormal(),
    )(block_input)
    x = tf.keras.layers.BatchNormalization()(x)
    return tf.nn.relu(x)


def AtrousSpatialPyramidPooling(aspp_input):

    dims = tf.keras.backend.int_shape(aspp_input)

    layer = tf.keras.layers.AveragePooling2D(pool_size=(dims[-3], dims[-2]))(aspp_input)
    layer = convolution_block(layer, kernel_size=1, use_bias=True)

    out_pool = tf.keras.layers.UpSampling2D(
        size=(dims[-3] // layer.shape[1], dims[-2] // layer.shape[2]),
        interpolation="bilinear",
    )(layer)

    out_1 = convolution_block(aspp_input, kernel_size=1, dilation_rate=1)
    out_6 = convolution_block(aspp_input, kernel_size=3, dilation_rate=6)
    out_12 = convolution_block(aspp_input, kernel_size=3, dilation_rate=12)
    out_18 = convolution_block(aspp_input, kernel_size=3, dilation_rate=18)

    layer = tf.keras.layers.Concatenate(axis=-1)(
        [out_pool, out_1, out_6, out_12, out_18]
    )

    output = convolution_block(layer, kernel_size=1)

    return output


"""
The encoder features are first bilinearly upsampled by a factor of 4 and then 
concatenated with the corresponding low-level features from the network backbone that
have the same spatial resolution. For this example, we would be 
using Resnet50 pre-trained on ImageNet as the backbone model and we would use 
the low-level features from the Conv2 block of the backbone.
"""


def DeeplabV3Plus():
    model_input = tf.keras.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3))
    resnet50 = tf.keras.applications.ResNet50(
        weights="imagenet", include_top=False, input_tensor=model_input
    )
    layer = resnet50.get_layer("conv4_block6_2_relu").output
    layer = AtrousSpatialPyramidPooling(layer)

    input_a = tf.keras.layers.UpSampling2D(
        size=(IMAGE_SIZE // 4 // layer.shape[1], IMAGE_SIZE // 4 // layer.shape[2]),
        interpolation="bilinear",
    )(layer)

    input_b = resnet50.get_layer("conv2_block3_2_relu").output
    input_b = convolution_block(input_b, n_filters=48, kernel_size=1)

    layer = tf.keras.layers.Concatenate(axis=-1)([input_a, input_b])
    layer = convolution_block(layer)
    layer = convolution_block(layer)
    layer = tf.keras.layers.UpSampling2D(
        size=(IMAGE_SIZE // layer.shape[1], IMAGE_SIZE // layer.shape[2]),
        interpolation="bilinear",
    )(layer)

    model_output = tf.keras.layers.Conv2D(
        NUM_CLASSES, kernel_size=(1, 1), padding="same"
    )(layer)

    return tf.keras.Model(inputs=model_input, outputs=model_output)


model = DeeplabV3Plus()
model.summary()

"""
## Training
"""

"""
We would train the model using Sparse Categorical Cross-entropy as the loss function and
use Adam as the optimizer.
"""

loss = tf.losses.SparseCategoricalCrossentropy(from_logits=True)
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss=loss,
    metrics=["accuracy"],
)
model.fit(dataset, epochs=25)

plt.plot(history.history["loss"])
plt.title("Training Loss")
plt.ylabel("loss")
plt.xlabel("epoch")
plt.show()

plt.plot(history.history["accuracy"])
plt.title("Training Accuracy")
plt.ylabel("accuracy")
plt.xlabel("epoch")
plt.show()

"""
## Inference using Colormap Overlay
"""

colormap = loadmat(
    "./instance-level_human_parsing/instance-level_human_parsing/human_colormap.mat"
)["colormap"]
colormap = colormap * 100
colormap = colormap.astype(np.uint8)


def infer(model, image_tensor):
    predictions = model.predict(np.expand_dims((image_tensor), axis=0))
    predictions = np.squeeze(predictions)
    predictions = np.argmax(predictions, axis=2)
    return predictions


def decode_segmask(mask, colormap, n_classes):
    r = np.zeros_like(mask).astype(np.uint8)
    g = np.zeros_like(mask).astype(np.uint8)
    b = np.zeros_like(mask).astype(np.uint8)
    for l in range(0, n_classes):
        idx = mask == l
        r[idx] = colormap[l, 0]
        g[idx] = colormap[l, 1]
        b[idx] = colormap[l, 2]
    rgb = np.stack([r, g, b], axis=2)
    return rgb


def get_overlay(image, colored_mask):
    image = tf.keras.preprocessing.image.array_to_img(image)
    image = np.array(image).astype(np.uint8)
    overlay = cv2.addWeighted(image, 0.35, colored_mask, 0.65, 0)
    return overlay


def plot_samples_matplotlib(display_list, figsize=(5, 3)):
    _, axes = plt.subplots(nrows=1, ncols=len(display_list), figsize=figsize)
    for i in range(len(display_list)):
        if display_list[i].shape[-1] == 3:
            axes[i].imshow(tf.keras.preprocessing.image.array_to_img(display_list[i]))
        else:
            axes[i].imshow(display_list[i])
    plt.show()


def plot_predictions(images_list, colormap, model):
    for image_file in images_list:
        image_tensor = read_image(image_file)
        prediction_mask = infer(image_tensor=image_tensor, model=model)
        prediction_colormap = decode_segmask(prediction_mask, colormap, 20)
        overlay = get_overlay(image_tensor, prediction_colormap)
        plot_samples_matplotlib(
            [image_tensor, overlay, prediction_colormap], figsize=(18, 14)
        )


plot_predictions(train_images[:4], colormap, model=model)
