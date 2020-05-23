"""
Title: FILLME
Author: FILLME
Date created: FILLME
Last modified: FILLME
Description: FILLME
"""
"""
# PixelCNN
**Author:** [ADMoreau](https://github.com/ADMoreau)  
**Date Created:** 2020/05/17  
**Last Modified:** 2020/05/23  
**Description:** PixelCNN implemented in Keras
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras, nn
from tensorflow.keras import layers

"""
##Getting the Data
"""

# Model / data parameters
num_classes = 10
input_shape = (28, 28, 1)
n_residual_blocks = 5
# the data, split between train and test sets
(x, _), (y, _) = keras.datasets.mnist.load_data()
# Concatenate all of the images together
data = np.concatenate((x, y), axis=0)
# round all pixel values less than 33% of the max 256 value to 0
# anything above this value gets rounded up to 1 so that all values are either
# 0 or 1
data = np.where(data < (0.33 * 256), 0, 1)
data = data.astype(np.float32)

"""
##Create two classes for the requisite Layers for the model
"""

# the first layer to create will be the PixelCNN layer, this layer simply
# builds on the 2D convolutional layer but with the requisite masking included
class PixelConvLayer(layers.Layer):
    def __init__(self, mask_type, **kwargs):
        super(PixelConvLayer, self).__init__()
        self.mask_type = mask_type
        self.conv = layers.Conv2D(**kwargs)

    def build(self, input_shape):
        # build the conv2d layer to initialize kernel variables
        self.conv.build(input_shape)
        # use said initialized kernel to develop the mask
        kernel_shape = self.conv.kernel.get_shape()
        self.mask = np.zeros(shape=kernel_shape)
        self.mask[: kernel_shape[0] // 2, ...] = 1.0
        self.mask[kernel_shape[0] // 2, : kernel_shape[1] // 2, ...] = 1.0
        if self.mask_type == "B":
            self.mask[kernel_shape[0] // 2, kernel_shape[1] // 2, ...] = 1.0

    def call(self, inputs):
        self.conv.kernel.assign(self.conv.kernel * self.mask)
        return self.conv(inputs)


# Next we build our residual block layer,
# this is just a normal residual block but with the PixelConvLayer built in
class ResidualBlock(keras.layers.Layer):
    def __init__(self, filters, **kwargs):
        super(ResidualBlock, self).__init__(**kwargs)
        self.a = keras.layers.ReLU()
        self.b = keras.layers.Conv2D(filters=filters, kernel_size=1, activation="relu")
        self.c = PixelConvLayer(
            mask_type="B",
            filters=filters // 2,
            kernel_size=3,
            activation="relu",
            padding="same",
        )
        self.d = keras.layers.Conv2D(filters=filters, kernel_size=1, activation="relu")

    def call(self, inputs):
        x = self.a(inputs)
        x = self.b(x)
        x = self.c(x)
        x = self.d(x)
        return keras.layers.add([inputs, x])


"""
## Build the model based on the original paper
"""

inputs = keras.Input(shape=input_shape)
x = PixelConvLayer(
    mask_type="A", filters=128, kernel_size=7, padding="same", activation="relu"
)(inputs)

for _ in range(n_residual_blocks):
    x = ResidualBlock(filters=128)(x)
x = layers.ReLU()(x)

for _ in range(2):
    x = PixelConvLayer(
        mask_type="B",
        filters=128,
        kernel_size=1,
        strides=1,
        activation="relu",
        padding="valid",
    )(x)

out = keras.layers.Conv2D(
    filters=1, kernel_size=1, strides=1, activation="sigmoid", padding="valid"
)(x)

PixelCNN = keras.Model(inputs, out)
adam = keras.optimizers.Adam(learning_rate=0.0001)
PixelCNN.compile(optimizer=adam, loss="binary_crossentropy")

PixelCNN.summary()
PixelCNN.fit(x=data, y=data, batch_size=64, epochs=50, validation_split=0.1)

"""
## Demonstration

The PixelCNN cannot create the full image at once and must instead create each pixel in
order, append the next created pixel to current image, and feed the image back into the
model to repeat the process.
"""

from IPython.display import Image, display
from tqdm import tqdm
import tensorflow_probability as tfp

# Create an empty array of pixels.
batch = 4
pixels = np.zeros(shape=(batch,) + (PixelCNN.input_shape)[1:])
batch, rows, cols, channels = pixels.shape

# Iterate the pixels because generation has to be done sequentially pixel by pixel.
for row in tqdm(range(rows)):
    for col in range(cols):
        for channel in range(channels):
# Feed the whole array and retrieving the pixel value probabilities for the next
#pixel.
            probs = PixelCNN.predict(pixels)[:, row, col, channel]
# Use the probabilities to pick pixel values and append the values to the image
#frame.
            pixels[:, row, col, channel] = tfp.distributions.Bernoulli(
                probs=probs
            ).sample()


def deprocess_image(x):
    # stack the single channeled black and white image to rgb values.
    x = np.stack((x, x, x), 2)
    # Undo preprocessing
    x *= 255.0
    # Convert to uint8 and clip to the valid range [0, 255]
    x = np.clip(x, 0, 255).astype("uint8")
    return x


# Iterate the generated images and plot them with matplotlib.
for i, pic in enumerate(pixels):
    keras.preprocessing.image.save_img(
        "generated_image_{}.png".format(i), deprocess_image(np.squeeze(pic, -1))
    )

display(Image("generated_image_0.png"))
display(Image("generated_image_1.png"))
display(Image("generated_image_2.png"))
display(Image("generated_image_3.png"))
