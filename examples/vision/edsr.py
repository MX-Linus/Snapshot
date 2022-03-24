"""
Title: Enhanced Deep Residual Networks for Single Image Super-Resolution
Author: Gitesh Chawda
Date created: 25-03-2022
Last modified: 25-03-2022
Description: Implementing EDSR model on DIV2K Dataset.
"""

"""
## Introduction 

Enhanced Deep Residual Networks for Single Image Super-Resolution
[EDSR](https://arxiv.org/abs/1707.02921) by Bee Lim, Sanghyun Son, Heewon Kim, Seungjun
Nah, Kyoung Mu Lee.

The EDSR architecture is based on the SRResNet architecture, consisting of multiple
residual blocks. It uses constant scaling layers instead of batch normalisation layers to
provide consistent training (input and output have similar distributions, thus
normalising intermediate features may not be desirable). Instead of using L2 (MSE), the
authors employed an L1 loss function (absolute error), which performed better empirically
and required less computation.
In this code example we will implementing base model that includes just 16 ResBlocks and
64 channels.

Alternatively, as shown in the Keras example 
[Image Super-Resolution using an Efficient Sub-Pixel CNN](https://keras.io/examples/vision/super_resolution_sub_pixel/#image-superresolution-using-an-efficient-subpixel-cnn), 
you can create an ESPCN Model. According to the survey paper, EDSR is one of the top five best-performing methods based on PSNR value, despite
the fact that it has more parameters and requires more computational power than other
approaches. It has a PSNR(≈34 db) value that is slightly higher than ESPCN(≈32 db).

As per the survey paper EDSR performs well than ESPCN. Paper : 
[A comprehensive review of deep learningbased single image super-resolution](https://arxiv.org/abs/2102.09351)

Comparison Graph :

<img src="https://dfzljdn9uc3pi.cloudfront.net/2021/cs-621/1/fig-11-2x.jpg" width="500" />
"""

"""
## Imports
"""

import numpy as np
import tensorflow as tf
import tensorflow_datasets as tfds
import matplotlib.pyplot as plt

from tensorflow import keras
from tensorflow.keras import layers

AUTOTUNE = tf.data.AUTOTUNE

"""
## Downloading Training Dataset

Using the DIV2K Dataset, a prominent single-image super-resolution dataset with 1,000
images of various scenarios divided into 800 for training, 100 for validation, and 100
for testing. Low-resolution images with various sorts of degradations are included in
this dataset. As a low quality image, We will be using x4 bicubic downsampled images.
"""

# Downloading DIV2K Dataset from tensorflow datasets
# Using bicubic x4 degradation type
div2k_data = tfds.image.Div2k(config="bicubic_x4")
div2k_data.download_and_prepare()

# Taking train data from div2k_data object
train = div2k_data.as_dataset(split="train", as_supervised=True)
train_cache = train.cache()
# Validation data
val = div2k_data.as_dataset(split="validation", as_supervised=True)
val_cache = val.cache()

"""
## Flip, crop and resize images
"""


def flip_left_right(lowres_img, highres_img):
    """
    Flipes Images to left and right
    """
    # Outputs random values from a uniform distribution in between 0 to 1
    rn = tf.random.uniform(shape=(), maxval=1)
    # If rn is less than 0.5 it returns original lowres_img and highres_img
    # If rn is greater than 0.5 it returns flipped image
    return tf.cond(rn < 0.5,
                   lambda: (lowres_img, highres_img),
                   lambda: (tf.image.flip_left_right(lowres_img),
                            tf.image.flip_left_right(highres_img)))


def random_rotate(lowres_img, highres_img):
    """
    Rotates Images by 90 degree
    """
    # Outputs random values from uniform distribution in between 0 to 4
    rn = tf.random.uniform(shape=(), maxval=4, dtype=tf.int32)
    # Here rn signifies number of times the image(s) are rotated by 90 degrees
    return tf.image.rot90(lowres_img, rn), tf.image.rot90(highres_img, rn)


def random_crop(lowres_img, highres_img, hr_crop_size=96, scale=4):
    """
    Cropping Images
    low resolution images : 24x24
    hight resolution images : 96x96
    """
    lowres_crop_size = hr_crop_size // scale #96//4=24
    lowres_img_shape = tf.shape(lowres_img)[:2] #(height,width)

    lowres_width = tf.random.uniform(shape=(), maxval=lowres_img_shape[1] - lowres_crop_size + 1, dtype=tf.int32) 
    lowres_height = tf.random.uniform(shape=(), maxval=lowres_img_shape[0] - lowres_crop_size + 1, dtype=tf.int32)

    highres_width = lowres_width * scale
    highres_height = lowres_height * scale

    lowres_img_cropped = lowres_img[lowres_height:lowres_height + lowres_crop_size, lowres_width:lowres_width + lowres_crop_size] #24x24
    highres_img_cropped = highres_img[highres_height:highres_height + hr_crop_size, highres_width:highres_width + hr_crop_size] #96x96

    return lowres_img_cropped, highres_img_cropped


"""
## Preparing tf.Data.Dataset object

As the paper suggest to use RGB input patches of size 48×48 from lowres image with the
corresponding highres patches. We augment the training data with random horizontal flips
and 90 rotations.

However, for lowres, we'll use 24x24 RGB input patches and corresponding highres patches
(96x96).
"""


def dataset_object(dataset_cache, train=True):
    
    ds = dataset_cache
    ds = ds.map(lambda lowres, highres: random_crop(lowres, highres, scale=4),num_parallel_calls=AUTOTUNE)
    
    if train:
        ds = ds.map(random_rotate,num_parallel_calls=AUTOTUNE)
        ds = ds.map(flip_left_right,num_parallel_calls=AUTOTUNE)
    # Batching Data
    ds = ds.batch(16)
    
    if train:
        # Repeating Data, so that cardinality if dataset becomes infinte
        ds = ds.repeat(None)
    # prefetching allows later images to be prepared while the current image is being processed 
    ds = ds.prefetch(buffer_size=AUTOTUNE)
    return ds


train_ds = dataset_object(train_cache, train=True)
val_ds = dataset_object(val_cache, train=False)

"""
## Let's visualize a few sample images:
"""

lowres, highres = next(iter(train_ds))

# Hight Resolution Images
plt.figure(figsize=(10, 10))
for i in range(9):
    ax = plt.subplot(3, 3, i + 1)
    plt.imshow(highres[i].numpy().astype("uint8"))
    plt.title(highres[i].shape)
    plt.axis("off")

# Low Resolution Images
plt.figure(figsize=(10, 10))
for i in range(9):
    ax = plt.subplot(3, 3, i + 1)
    plt.imshow(lowres[i].numpy().astype("uint8"))
    plt.title(lowres[i].shape)
    plt.axis("off")


def PSNR(super_resolution, high_resolution):
    """
    Computes the peak signal-to-noise ratio, measures quality of image.
    """
    # Max value of pixel is 255
    psnr_value = tf.image.psnr(high_resolution, super_resolution, max_val=255)[0]
    return psnr_value


"""
## Build a model

In paper authors hav trained 3 models : EDSR, MDSR and baseline, so for this code example
we will be training baseline model.

### Comparison of 3 residual blocks

Authors compared 3 residual blocks from original resnet, SRResNet and proposed. The only
difference is removal of batch normalization layer, Since batch normalization layers
normalize the features, they get rid of range flexibility from networks by normalizing
the features, it is better to remove them, Furthermore, GPU memory usage is also
sufficiently reduced since the batch normalization layers consume the same amount of
memory as the preceding convolutional layers.

<img src="https://miro.medium.com/max/1050/1*EPviXGqlGWotVtV2gqVvNg.png" width="500" /> 
"""

# Residual Block
def ResBlock(inputs):
    x = layers.Conv2D(64, 3, padding="same", activation="relu")(inputs)
    x = layers.Conv2D(64, 3, padding="same")(x)
    x = layers.Add()([inputs, x])
    return x


# Upsampling Block
def Upsampling(inputs, factor=2, **kwargs):
    x = layers.Conv2D(64 * (factor**2), 3, padding="same", **kwargs)(inputs)
    x = tf.nn.depth_to_space(x, block_size=factor)
    x = layers.Conv2D(64 * (factor**2), 3, padding="same", **kwargs)(x)
    x = tf.nn.depth_to_space(x, block_size=factor)
    return x


def EDSR_MODEL(num_filters, no_of_residual_blocks):
    # Flexible Inputs to input_layer
    input_layer = layers.Input(shape=(None, None, 3))
    # Scaling Pixel Values
    x = layers.Rescaling(scale=1.0 / 255)(input_layer)
    x = x_new = layers.Conv2D(num_filters, 3, padding="same")(x)

    # 16 residual blocks
    for _ in range(no_of_residual_blocks):
        x_new = ResBlock(x_new)

    x_new = layers.Conv2D(num_filters, 3, padding="same")(x_new)
    x = layers.Add()([x, x_new])

    x = Upsampling(x)
    x = layers.Conv2D(3, 3, padding="same")(x)

    output_layer = layers.Rescaling(scale=255)(x)
    return keras.Model(input_layer, output_layer)


class CustomModel(tf.keras.Model):
    def train_step(self, data):
        # Unpack the data. Its structure depends on your model and
        # on what you pass to `fit()`.
        x, y = data

        with tf.GradientTape() as tape:
            y_pred = self(x, training=True)  # Forward pass
            # Compute the loss value
            # (the loss function is configured in `compile()`)
            loss = self.compiled_loss(y, y_pred, regularization_losses=self.losses)

        # Compute gradients
        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)
        # Update weights
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        # Update metrics (includes the metric that tracks the loss)
        self.compiled_metrics.update_state(y, y_pred)
        # Return a dict mapping metric names to current value
        return {m.name: m.result() for m in self.metrics}
    
    def predict_step(self, x):
        # Adding dummy dimension using tf.expand_dims and converting to float32 using tf.cast
        x = tf.cast(tf.expand_dims(x, axis=0), tf.float32)
        # Passing low resolution image to model
        super_resolution_img = self(x, training=False)
        # Clips the tensor from min(0) to max(255)
        super_resolution_img = tf.clip_by_value(super_resolution_img, 0, 255)
        # Rounds the values of a tensor to the nearest integer
        super_resolution_img = tf.round(super_resolution_img)
        # Removes dimensions of size 1 from the shape of a tensor and converting to uint8
        super_resolution_img = tf.squeeze(tf.cast(super_resolution_img, tf.uint8),axis=0)
        return super_resolution_img


# Calling EDSR_MODEL function
edsr = EDSR_MODEL(num_filters=64, no_of_residual_blocks=16)
# Creating object of CustomModel
model = CustomModel(edsr.inputs, edsr.outputs)

"""
## Train the model
"""

# Using adam optimizer with initial learning rate as 1e-4, changing learning rate after 5000 steps to 5e-5
optim_edsr = tf.keras.optimizers.Adam(learning_rate=keras.optimizers.schedules.PiecewiseConstantDecay(boundaries=[5000], 
                                                                                                      values=[1e-4, 5e-5]))
# Compiling model with loss as mean absolute error(L1 Loss) and metric as psnr
model.compile(optimizer = optim_edsr, loss = 'mae', metrics = [PSNR])
model.fit(train_ds, epochs = 100, steps_per_epoch = 200, validation_data = val_ds)

"""
## Run model prediction and plot the results

"""

def plot_results(x):
    """
    Displays low resolution image and super resolution image
    """
    plt.figure(figsize=(24, 14))
    plt.subplot(132), plt.imshow(x), plt.title("Low resolution")
    plt.subplot(133), plt.imshow(model.predict_step(x)), plt.title("Prediction")
    plt.show()


for lowres, highres in val.take(10):
    lowres = tf.image.random_crop(lowres, (150, 150, 3))
    plot_results(lowres)
