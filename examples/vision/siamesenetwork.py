"""
Title: Siamese Network with Triplet Loss
Author: [hazemessamm](https://twitter.com/hazemessamm) and [Santiago L. Valdarrama](https://twitter.com/svpino)
Date created: 2021/03/13
Last modified: 2021/03/22
Description: Siamese network with custom data generator and training loop.
"""
"""
### Setup
"""

import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import random
import os

from pathlib import Path
from tensorflow.keras import losses, optimizers
from tensorflow.keras import layers
from tensorflow.keras import Model
from tensorflow.keras import applications
from tensorflow.keras import preprocessing
from tensorflow.keras.utils import Sequence

"""
# Load the dataset

Let's download the [Totally Looks Like dataset](https://drive.google.com/drive/folders/1qQJHA5m-vLMAkBfWEWgGW9n61gC_orHl) and unzip it in our local directory.

We will end up with two different directories:
* `left` contains the images that we will use as the anchor.
* `right` contains the images that we will use as the positive sample (an image that looks like the anchor.)
"""

cache_dir = Path(os.path.expanduser("~")) / ".keras"
anchor_images_path = cache_dir / "left"
positive_images_path = cache_dir / "right"

"""shell
gdown --id 1jvkbTr_giSP3Ru8OwGNCg6B4PvVbcO34
gdown --id 1EzBZUb_mh_Dp_FKD0P4XiYYSd0QBH5zW
unzip -oq left.zip -d $cache_dir
unzip -oq right.zip -d $cache_dir
"""

"""
## Siamese Network

[Siamese Network](https://en.wikipedia.org/wiki/Siamese_neural_network) is used to solve
many problems like detecting question duplicates, face recognition by comparing the
similarity of the inputs by comparing their feature vectors.

First we need to have a dataset that contains 3 Images, 2 are similar and 1 is different,
they are called Anchor image, Positive Image and Negative image respectively, we need to
tell the network that the anchor image and the positive image are similar, we also need
to tell it that the anchor image and the negative image are NOT similar, we can do that
by the Triplet Loss Function.

Triplet Loss function:

L(Anchor, Positive, Negative) = max((distance(f(Anchor), f(Positive)) -
distance(f(Anchor), f(Negative)))**2, 0.0)

Note that the weights are shared which mean that we are only using one model for
prediction and training

Also more info found here: https://sites.google.com/view/totally-looks-like-dataset

Image from:
https://towardsdatascience.com/a-friendly-introduction-to-siamese-networks-85ab17522942


![1_0E9104t29iMBmtvq7G1G6Q.png](attachment:1_0E9104t29iMBmtvq7G1G6Q.png)
"""

"""
First we get the paths of the datasets in siamese networks we usually have two folders
each folder has images and every image has a corresponding similar picture in the other
folder.
"""

"""
## Preparing data
"""

target_shape = (200, 200)
anchor_images = [str(anchor_images_path / f) for f in os.listdir(anchor_images_path)]


def preprocess_image(filename):
    image_string = tf.io.read_file(filename)
    image = tf.image.decode_jpeg(image_string, channels=3)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.resize(image, target_shape)
    return image


def generate_negative_sample(t: tf.Tensor):
    filename = t.numpy().decode("utf-8")
    candidate = filename
    while candidate == filename:
        candidate = random.choice(anchor_images).split(os.sep)[-1]

    folder = random.choice([anchor_images_path, positive_images_path])

    return str(folder / candidate)


def generate_triplets(anchor_sample):
    parts = tf.strings.split(anchor_sample, os.sep)
    filename = parts[-1]

    positive_sample = f"{str(positive_images_path)}{os.sep}" + filename

    negative_sample = tf.py_function(
        func=generate_negative_sample, inp=[filename], Tout=tf.string
    )

    return anchor_sample, positive_sample, negative_sample


def preprocess_triplets(anchor, positive, negative):
    return (
        preprocess_image(anchor),
        preprocess_image(positive),
        preprocess_image(negative),
    )


dataset = tf.data.Dataset.from_tensor_slices(anchor_images)
dataset = dataset.shuffle(buffer_size=100)
dataset = dataset.map(generate_triplets)
dataset = dataset.map(preprocess_triplets)
dataset = dataset.batch(32, drop_remainder=False)
dataset = dataset.prefetch(1)

# this function just visalize each random 3 images (anchor, positive, negative)
def visualize(x):
    anchor, positive, negative = x
    f, (ax1, ax2, ax3) = plt.subplots(1, 3)
    ax1.imshow(anchor[0])
    ax2.imshow(positive[0])
    ax3.imshow(negative[0])


visualize(next(iter(dataset)))

"""
## Loading a pre-trained model
"""

"""
Here we use ResNet50 architecture, we use "imagenet" weights, also we pass the image shape
Note that include_top means that we do NOT want the top layers
"""

base_cnn = applications.ResNet50(
    weights="imagenet", input_shape=target_shape + (3,), include_top=False
)

"""
## Fine Tuning
"""

"""
Here we fine tune the ResNet50 we freeze all layers that exist before "conv5_block1_out"
layer, starting from "conv5_block2_2_relu" layer we unfreeze all the layers so we can
just train these layers
"""

trainable = False
for layer in base_cnn.layers:
    if layer.name == "conv5_block1_out":
        trainable = True
    layer.trainable = trainable

"""
## Adding top layers
"""

"""
Here we customize the model by adding Dense layers and Batch Normalization layers. we
start with the image input then we pass the input to the base_cnn then we flatten it.
Finally we pass each layer as an input to the next layer the output layer is just a dense
layer which will act as an embedding for our images.
"""

flatten = layers.Flatten()(base_cnn.output)
dense1 = layers.Dense(512, activation="relu")(flatten)
dense1 = layers.BatchNormalization()(dense1)
dense2 = layers.Dense(256, activation="relu")(dense1)
dense2 = layers.BatchNormalization()(dense2)
output = layers.Dense(256)(dense2)

embedding = Model(base_cnn.input, output, name="SiameseNetwork")

embedding.summary()

"""
## Model for training
"""

"""
This model is just used for training we pass to it three input batches (anchor images,
positive images, negative images) and the output will be the output of the model we
defined above, it will be 1 output for each input.
"""

anchor_input = layers.Input(shape=target_shape + (3,))
positive_input = layers.Input(shape=target_shape + (3,))
negative_input = layers.Input(shape=target_shape + (3,))

anchor_output = embedding(anchor_input)
positive_output = embedding(positive_input)
negative_output = embedding(negative_input)

training_model = Model(
    [anchor_input, positive_input, negative_input],
    {
        "anchor_embedding": anchor_output,
        "positive_embedding": positive_output,
        "negative_embedding": negative_output,
    },
)


"""
## Cosine Similarity Layer
"""

"""

This layer just computes how similar to feature vectors are by computing it using the
Cosine Similarity
We override the call method and implement our own call method.

Check out https://www.tensorflow.org/api_docs/python/tf/keras/losses/CosineSimilarity

We return the negative of the loss because we just need to know how similar they are we
do NOT need to know the loss
"""


class CosineDistance(layers.Layer):
    def __init__(self):
        super(CosineDistance, self).__init__()

    def call(self, img1, img2):
        return -losses.CosineSimilarity(reduction=losses.Reduction.NONE)(img1, img2)


"""
## Model subclassing
"""

"""
Here we customize our training process and our model.

We override the train_step() method and apply our own loss and our own training process

We also use Triplet loss function as we specified above.

Loss function explaination:

we calculate the distance between the anchor embedding and the positive embedding the
axis = -1 because we want the distance over the features of every example. We also add
alpha which act as extra margin.
"""


class SiameseModel(Model):
    def __init__(self, model, alpha=0.5):
        super(SiameseModel, self).__init__()
        self.embedding = model  # we pass the model to the class
        self.alpha = alpha

    def call(self, inputs):
        pass

    def train_step(self, data):
        # here we create a tape to record our operations so we can get the gradients
        with tf.GradientTape() as tape:
            anchor, positive, negative = data
            embeddings = training_model((anchor, positive, negative))

            # Euclidean Distance between anchor and positive
            # axis=-1 so we can get distances over examples
            anchor_positive_dist = tf.reduce_sum(
                tf.square(
                    embeddings["anchor_embedding"] - embeddings["positive_embedding"]
                ),
                -1,
            )

            # Euclidean Distance between anchor and negative
            anchor_negative_dist = tf.reduce_sum(
                tf.square(
                    embeddings["anchor_embedding"] - embeddings["negative_embedding"]
                ),
                -1,
            )

            # getting the loss by subtracting the distances
            loss = anchor_positive_dist - anchor_negative_dist
            # getting the max because we don't want negative loss
            loss = tf.reduce_mean(tf.maximum(loss + self.alpha, 0.0))
        # getting the gradients [loss with respect to trainable weights]
        grads = tape.gradient(loss, training_model.trainable_weights)
        # applying the gradients on the model using the specified optimizer
        self.optimizer.apply_gradients(zip(grads, training_model.trainable_weights))
        return {"Loss": loss}


"""
### Training
"""

siamese_model = SiameseModel(embedding)

siamese_model.compile(optimizer=optimizers.Adam(0.0001))

siamese_model.fit(dataset, epochs=3)

"""
### Inference
"""

example_prediction = next(iter(dataset))
visualize(example_prediction)

anchor_tensor, positive_tensor, negative_embedding = example_prediction
anchor_embedding, positive_embedding, negative_embedding = (
    embedding(anchor_tensor),
    embedding(positive_tensor),
    embedding(negative_embedding),
)

positive_similarity = CosineDistance()(anchor_embedding, positive_embedding)
print("Similarity between similar images:", positive_similarity[0])

negative_similarity = CosineDistance()(anchor_embedding, negative_embedding)
print("Similarity between dissimilar images:", negative_similarity[0])

"""
### Key Takeaways

1) You can create your custom data generator by creating a class that inherits from
tf.keras.utils.Sequence, as we saw, this is really helpful if we want to generate data in
different forms like Anchor, Positive and negative in our case, you just need to
implement the __len__() and __getitem__(). Check out the documentation
https://www.tensorflow.org/api_docs/python/tf/keras/utils/Sequence

2) If you don't have the computation power to train large models like ResNet-50 or if you
don't have the time to re-write really big models you can just download it with one line,
e.g. tf.keras.applications.ResNet50().

3) Every layer has a name, this is really helpful for fine tuning, If you want to fine
tune specific layers, in our example we loop over the layers until we find specific layer
by it's name and we made it trainable, this allows the weights of this layer to change
during training

4) In our example we have only one embedding network that we need to train it but we need
3 outputs to compare them with each other, we can do that by creating a model that have 3
input layers and each input will pass through the embedding network and then we will have
3 outputs embeddings, we did that in the "Model for Training section".

5) You can name your output layers like we did in the "Model for Training section", you
just need to create a dictionary with keys as the name of your output layer and the
output layers as values.

6) We used cosine similarity to measure how to 2 output embeddings are similar to each
other.

6) You can create your custom Layers by just creating a class that inherits from
tf.keras.layers.Layer, you just need to implement the call function. check out the
documentation https://www.tensorflow.org/api_docs/python/tf/keras/layers/Layer

7) If you want to have custom training loop you can create your own model class that
inherits from tf.keras.Model, you just need to override the train_step function and add
you implementation.

8) You can get your model gradients by using tf.GradientTape(), GradientTape records the
operations that you do inside it, so you can get the predictions and write your custom
loss function inside the GradientTape as we did.

9) You can get the gradients using tape.gradient(loss, model.trainable_weights), this
means that we need the gradients of the loss with respect to the model trainable weights,
where "tape" is the name of our tf.GradientTape() in our example.

10) you can just pass the gradients and the model weights to the optimizer to update them.

For more info about GradientTape check out
https://keras.io/getting_started/intro_to_keras_for_researchers/ and
https://www.tensorflow.org/api_docs/python/tf/GradientTape
"""
