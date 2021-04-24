"""
Title: Semi-supervised image classification using contrastive pretraining with SimCLR
Author: [András Béres](www.linkedin.com/in/andras-beres-789190210)
Date created: 2021/04/24
Last modified: 2021/04/24
Description: Using SimCLR for contrastive pretraining for semi-supervised image classification.
"""
"""
## Introduction

### Semi-supervised learning

Semi-supervised learning is a machine learning paradigm, that deals with **partially
labeled datasets**. When applying deep learning in the real world, one usually has to
gather a large dataset to make it work well. However, while the cost of labeling scales
linearly with the dataset size (labeling each example takes a constant time), model
performance only scales [sublinearly](https://arxiv.org/abs/2001.08361) with it. This
means that labeling more and more samples becomes less and less cost-efficient, while
gathering unlabeled data is generally cheap as it is usually readily available in large
quantities.

Semi-supervised learning offers to solve this problem by only requiring a partially
labeled dataset, and by being label-efficient by utilizing the unlabeled examples for
learning as well.

In this example, we will pretrain an encoder with contrastive learning on the
[STL10](https://ai.stanford.edu/~acoates/stl10/) semi-supervised dataset using no labels
at all, and then finetune it using only its labeled subset.

### Contrastive learning

On the highest level, the main idea of contrastive learning is to **learn representations
that are invariant to image augmentations** in a self-supervised manner. One problem with
this objective is that it has a trivial degenerate solution, when the sepresentations are
constant, and do not depend at all on the input images.

Contrastive learning avoids this condition by modifying the objective in the following
way: it pulls representations of augmented versions/views of the same image closer to
each other (contracting positives), while simultaneously pushing different images away
from each other (contrasting negatives) in representation space.

One such contrastive approach is [SimCLR](https://arxiv.org/abs/2002.05709), which
essentially identifies the core components needed to optimize this objective, and
achieves a high performance by scaling this simple approach. For further reading about
SimCLR check out [its
blogpost](https://ai.googleblog.com/2020/04/advancing-self-supervised-and-semi.html), for
an overview of self-supervised learning across both vision and language check out [this
blogpost](https://ai.facebook.com/blog/self-supervised-learning-the-dark-matter-of-intelligence/).
"""

"""
## Setup
"""

import random
import math
import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow_datasets as tfds

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.layers.experimental import preprocessing

"""
## Hyperparameterers
"""

num_epochs = 60
steps_per_epoch = 200  # defines the batch size implicitly
width = 128
temperature = 0.1

"""
## Dataset

During training we will load a large batch of unlabeled images along with a smaller batch
of labeled images simultaneously.
"""


def prepare_dataset(steps_per_epoch):
    # labeled and unlabeled samples are loaded synchronously
    # with batch sizes selected accordingly
    unlabeled_batch_size = 100000 // steps_per_epoch
    labeled_batch_size = 5000 // steps_per_epoch
    batch_size = unlabeled_batch_size + labeled_batch_size
    print(
        "batch size is {} (unlabeled) + {} (labeled)".format(
            unlabeled_batch_size, labeled_batch_size
        )
    )

    unlabeled_train_dataset = (
        tfds.load("stl10", split="unlabelled", as_supervised=True, shuffle_files=True)
        .shuffle(buffer_size=5000)
        .batch(unlabeled_batch_size, drop_remainder=True)
    )
    labeled_train_dataset = (
        tfds.load("stl10", split="train", as_supervised=True, shuffle_files=True)
        .shuffle(buffer_size=5000)
        .batch(labeled_batch_size, drop_remainder=True)
    )
    test_dataset = (
        tfds.load("stl10", split="test", as_supervised=True)
        .batch(batch_size)
        .prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    )

    # labeled and unlabeled datasets are zipped together
    train_dataset = tf.data.Dataset.zip(
        (unlabeled_train_dataset, labeled_train_dataset)
    ).prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

    return batch_size, train_dataset, labeled_train_dataset, test_dataset


# load STL10 dataset
batch_size, train_dataset, labeled_train_dataset, test_dataset = prepare_dataset(
    steps_per_epoch
)

"""
## Custom image augmentation layers

The two most important image augmentations for contrastive learning are the following:
- cropping: forces the model to encode different parts of the same image similarly
- color jitter: prevents a trivial color histogram-based solution to the task by
distorting color histograms

In this example we use random horizontal flips as well.

We implement our image augmentations as custom preprocessing layers. This has the
following two advantages:
- the data augmentation will run on the GPU, so the training will not be bottlenecked by
the data pipeline in environments with constrained CPU resources (such as a Colab
Notebook, or a personal machine)
- deployment is easier as the data preprocessing pipeline is encapsulated in the model,
and does not have to be reimplemented when deploying it
"""

# the implementation of these image augmentations follow the torchvision library:
# https://github.com/pytorch/vision/blob/master/torchvision/transforms/transforms.py
# https://github.com/pytorch/vision/blob/master/torchvision/transforms/functional_tensor.py

# however these augmentations:
# -run on batches of images
# -run on gpu
# -can be part of a model


# crops and resizes part of the image to the original resolutions
class RandomResizedCrop(layers.Layer):
    def __init__(self, scale, ratio, **kwargs):
        super().__init__(**kwargs)
        # area-range of the cropped part: (min area, max area), uniform sampling
        self.scale = scale
        # aspect-ratio-range of the cropped part: (log min ratio, log max ratio), log-uniform sampling
        self.log_ratio = (tf.math.log(ratio[0]), tf.math.log(ratio[1]))

    def call(self, images, training=True):
        if training:
            batch_size = tf.shape(images)[0]
            height = tf.shape(images)[1]
            width = tf.shape(images)[2]

            # independently sampled scales and ratios for every image in the batch
            random_scales = tf.random.uniform(
                (batch_size,), self.scale[0], self.scale[1]
            )
            random_ratios = tf.exp(
                tf.random.uniform((batch_size,), self.log_ratio[0], self.log_ratio[1])
            )

            # corresponding height and widths, clipped to fit in the image
            new_heights = tf.clip_by_value(tf.sqrt(random_scales / random_ratios), 0, 1)
            new_widths = tf.clip_by_value(tf.sqrt(random_scales * random_ratios), 0, 1)

            # random anchors for the crop bounding boxes
            height_offsets = tf.random.uniform((batch_size,), 0, 1 - new_heights)
            width_offsets = tf.random.uniform((batch_size,), 0, 1 - new_widths)

            # assemble bounding boxes and crop
            bounding_boxes = tf.stack(
                [
                    height_offsets,
                    width_offsets,
                    height_offsets + new_heights,
                    width_offsets + new_widths,
                ],
                axis=1,
            )
            images = tf.image.crop_and_resize(
                images, bounding_boxes, tf.range(batch_size), (height, width)
            )

        return images


# distorts the color distibutions of images
class RandomColorJitter(layers.Layer):
    def __init__(self, brightness=0, contrast=0, saturation=0, hue=0, **kwargs):
        super().__init__(**kwargs)

        # color jitter ranges: (min jitter strength, max jitter strength)
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.hue = hue

        # list of applicable color augmentations
        self.color_augmentations = [
            self.random_brightness,
            self.random_contrast,
            self.random_saturation,
            self.random_hue,
        ]

        # the tf.image.random_[brightness, contrast, saturation, hue] operations
        # cannot be used here, as they transform a batch of images in the same way

    def blend(self, images_1, images_2, ratios):
        # linear interpolation between two images, with values clipped to the valid range
        return tf.clip_by_value(ratios * images_1 + (1.0 - ratios) * images_2, 0, 1)

    def random_brightness(self, images):
        # random interpolation/extrapolation between the image and darkness
        return self.blend(
            images,
            0,
            tf.random.uniform(
                (tf.shape(images)[0], 1, 1, 1), 1 - self.brightness, 1 + self.brightness
            ),
        )

    def random_contrast(self, images):
        # random interpolation/extrapolation between the image and its mean intensity value
        mean = tf.reduce_mean(
            tf.image.rgb_to_grayscale(images), axis=(1, 2), keepdims=True
        )
        return self.blend(
            images,
            mean,
            tf.random.uniform(
                (tf.shape(images)[0], 1, 1, 1), 1 - self.contrast, 1 + self.contrast
            ),
        )

    def random_saturation(self, images):
        # random interpolation/extrapolation between the image and its grayscale counterpart
        return self.blend(
            images,
            tf.image.rgb_to_grayscale(images),
            tf.random.uniform(
                (tf.shape(images)[0], 1, 1, 1), 1 - self.saturation, 1 + self.saturation
            ),
        )

    def random_hue(self, images):
        # random shift in hue in hsv colorspace
        images = tf.image.rgb_to_hsv(images)
        images += tf.random.uniform(
            (tf.shape(images)[0], 1, 1, 3), (-self.hue, 0, 0), (self.hue, 0, 0)
        )
        # tf.math.floormod(images, 1.0) should be used here, however in introduces artifacts
        images = tf.where(images < 0.0, images + 1.0, images)
        images = tf.where(images > 1.0, images - 1.0, images)
        images = tf.image.hsv_to_rgb(images)
        return images

    def call(self, images, training=True):
        if training:
            # applies color augmentations in random order
            for color_augmentation in random.sample(self.color_augmentations, 4):
                images = color_augmentation(images)
        return images


"""
## Image augmentation modules

We use stronger augmentations for contrastive learning, along with weaker ones for
supervised classification to avoid overfitting on the few labeled examples.
"""

# stronger augmentations are used for the contrastive task
def get_contrastive_augmenter():
    return keras.Sequential(
        [
            layers.Input(shape=(96, 96, 3)),
            preprocessing.Rescaling(1 / 255),
            preprocessing.RandomFlip("horizontal"),
            RandomResizedCrop(scale=(0.2, 1.0), ratio=(3 / 4, 4 / 3)),
            RandomColorJitter(brightness=0.5, contrast=0.5, saturation=0.5, hue=0.2),
        ],
        name="contrastive_augmenter",
    )


# weaker augmentations are used for the classification task
def get_classification_augmenter():
    return keras.Sequential(
        [
            layers.Input(shape=(96, 96, 3)),
            preprocessing.Rescaling(1 / 255),
            preprocessing.RandomFlip("horizontal"),
            RandomResizedCrop(scale=(0.5, 1.0), ratio=(3 / 4, 4 / 3)),
            RandomColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
        ],
        name="classification_augmenter",
    )


def visualize_augmentations(num_images):
    # sample a batch from a dataset
    images = next(iter(train_dataset))[0][0][:num_images]
    # apply augmentations
    augmented_images = zip(
        images,
        get_classification_augmenter()(images),
        get_contrastive_augmenter()(images),
        get_contrastive_augmenter()(images),
    )

    row_titles = [
        "Original:",
        "Weakly augmented:",
        "Strongly augmented:",
        "Strongly augmented:",
    ]
    plt.figure(figsize=(num_images * 2.2, 4 * 2.2), dpi=100)
    for column, image_row in enumerate(augmented_images):
        for row, image in enumerate(image_row):
            plt.subplot(4, num_images, row * num_images + column + 1)
            plt.imshow(image)
            if column == 0:
                plt.title(row_titles[row], loc="left")
            plt.axis("off")
    plt.tight_layout()


visualize_augmentations(num_images=8)

"""
## Encoder architecture
"""

# define the encoder architecture
def get_encoder(width):
    return keras.Sequential(
        [
            layers.Input(shape=(96, 96, 3)),
            layers.Conv2D(width, kernel_size=3, strides=2, activation="relu"),
            layers.Conv2D(width, kernel_size=3, strides=2, activation="relu"),
            layers.Conv2D(width, kernel_size=3, strides=2, activation="relu"),
            layers.Conv2D(width, kernel_size=3, strides=2, activation="relu"),
            layers.Flatten(),
            layers.Dense(width, activation="relu"),
        ],
        name="encoder",
    )


"""
## Supervised baseline model

A baseline supervised model is trained using random initialization for 60 epochs.
"""

# baseline supervised training with random initialization
baseline_model = keras.Sequential(
    [
        layers.Input(shape=(96, 96, 3)),
        get_classification_augmenter(),
        get_encoder(width),
        layers.Dense(10),
    ],
    name="not_pretrained_model",
)
baseline_model.compile(
    optimizer=keras.optimizers.Adam(),
    loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=[keras.metrics.SparseCategoricalAccuracy(name="acc")],
)

baseline_history = baseline_model.fit(
    labeled_train_dataset, epochs=num_epochs, validation_data=test_dataset
)
print(
    "Maximal validation accuracy: {:.2f}%".format(
        max(baseline_history.history["val_acc"]) * 100
    )
)

"""
## Self-supervised model for contrastive pretraining

We pretrain an encoder on unlabeled images with a contrastive loss for 30 epochs. A
nonlinear projection head is attached to the top of the encoder, as it improves the
quality of representations of the encoder.

The InfoNCE/NT-Xent/N-pairs loss is used, which can be interpreted in the following way:
- we treat each image in the batch as if it had its own class
- then we have two examples (a pair of augmented views) for each "class"
- each view's representation is compared to every possible pair's one (for both augmented
versions)
- we use the temperature-scaled cosine similarity of compared representations as logits
- and use categorical cross-entropy as the "classification" loss

The following two metrics are used for monitoring the pretraining performance:
- **contrastive accuracy**: self-supervised metric, the ratio of cases in which the
closest representation to a view was its differently augmented version from the same
image. Self-supervised metrics can be used for hyperparameter tuning even in the case
when there are no labeled examples.
- **linear probing accuracy**: supervised metric, "linear probing" is a widely used
metric in the self-supervised literature. It simply means the accuracy of a logistic
regression classifier trained on the encoder's features, i.e. training a single linear
fully connected layer for classification on top of the frozen encoder. This classifier is
usually trained after the pretraining phase, however in this example, we train it during
pretraining, which might decrease its accuracy, but that way its value can be monitored
during training, which helps with experimentation and debugging.

Another widely used supervised metric is the [KNN
accuracy](https://arxiv.org/abs/1805.01978), which is the accuracy of a KNN classifier
trained on top of the encoder's features, which is not implemented in this example.
"""

# define the contrastive model with model-subclassing
class ContrastiveModel(keras.Model):
    def __init__(self, width, temperature):
        super().__init__()

        self.temperature = temperature

        self.contrastive_augmenter = get_contrastive_augmenter()
        self.classification_augmenter = get_classification_augmenter()
        self.encoder = get_encoder(width)
        # a non-linear mlp as projection head
        self.projection_head = keras.Sequential(
            [
                layers.Input(shape=(width,)),
                layers.Dense(width, activation="relu"),
                layers.Dense(width),
            ],
            name="projection_head",
        )
        # a single dense layer for linear probing
        self.linear_probe = keras.Sequential(
            [layers.Input(shape=(width,)), layers.Dense(10),], name="linear_probe",
        )

        self.contrastive_augmenter.summary()
        self.classification_augmenter.summary()
        self.encoder.summary()
        self.projection_head.summary()
        self.linear_probe.summary()

    def compile(self, contrastive_optimizer, probe_optimizer, **kwargs):
        super().compile(**kwargs)

        self.contrastive_optimizer = contrastive_optimizer
        self.probe_optimizer = probe_optimizer

        # self.contrastive_loss will be defined as a method
        self.probe_loss = keras.losses.SparseCategoricalCrossentropy(from_logits=True)

        self.contrastive_accuracy = keras.metrics.SparseCategoricalAccuracy()
        self.probe_accuracy = keras.metrics.SparseCategoricalAccuracy()

    def reset_metrics(self):
        self.contrastive_accuracy.reset_states()
        self.probe_accuracy.reset_states()

    def contrastive_loss(self, projections_1, projections_2):
        # InfoNCE loss (information noise-contrastive estimation)
        # NT-Xent loss (normalized temperature-scaled cross entropy)

        # cosine similarity: the dot product of the l2-normalized feature vectors
        projections_1 = tf.math.l2_normalize(projections_1, axis=1)
        projections_2 = tf.math.l2_normalize(projections_2, axis=1)
        similarities = (
            tf.matmul(projections_1, projections_2, transpose_b=True) / self.temperature
        )

        # the similarity between the representations of two augmented views of the
        # same image should be higher than their similarity with other views
        contrastive_labels = tf.range(batch_size)
        self.contrastive_accuracy.update_state(contrastive_labels, similarities)
        self.contrastive_accuracy.update_state(
            contrastive_labels, tf.transpose(similarities)
        )

        # the temperature-scaled similarities are used as logits for cross-entropy
        # a symmetrized version of the loss is used here
        loss = (
            keras.losses.sparse_categorical_crossentropy(
                contrastive_labels, similarities, from_logits=True
            )
            + keras.losses.sparse_categorical_crossentropy(
                contrastive_labels, tf.transpose(similarities), from_logits=True
            )
        ) / 2

        return loss

    def train_step(self, data):
        (unlabeled_images, _), (labeled_images, labels) = data

        # both labeled and unlabeled images are used, without labels
        images = tf.concat((unlabeled_images, labeled_images), axis=0)
        # each image is augmented twice, differently
        augmented_images_1 = self.contrastive_augmenter(images)
        augmented_images_2 = self.contrastive_augmenter(images)
        with tf.GradientTape() as tape:
            features_1 = self.encoder(augmented_images_1)
            features_2 = self.encoder(augmented_images_2)
            # the representations are passed through a projection mlp
            projections_1 = self.projection_head(features_1)
            projections_2 = self.projection_head(features_2)
            contrastive_loss = self.contrastive_loss(projections_1, projections_2)
        gradients = tape.gradient(
            contrastive_loss,
            self.encoder.trainable_weights + self.projection_head.trainable_weights,
        )
        self.contrastive_optimizer.apply_gradients(
            zip(
                gradients,
                self.encoder.trainable_weights + self.projection_head.trainable_weights,
            )
        )

        # labels are only used in evalutation for an on-the-fly logistic regression
        preprocessed_images = self.classification_augmenter(labeled_images)
        with tf.GradientTape() as tape:
            features = self.encoder(preprocessed_images)
            class_logits = self.linear_probe(features)
            probe_loss = self.probe_loss(labels, class_logits)
        gradients = tape.gradient(probe_loss, self.linear_probe.trainable_weights)
        self.probe_optimizer.apply_gradients(
            zip(gradients, self.linear_probe.trainable_weights)
        )
        self.probe_accuracy.update_state(labels, class_logits)

        return {
            "c_loss": contrastive_loss,
            "c_acc": self.contrastive_accuracy.result(),
            "p_loss": probe_loss,
            "p_acc": self.probe_accuracy.result(),
        }

    def test_step(self, data):
        labeled_images, labels = data

        # for testing the components are used with a training=False flag
        preprocessed_images = self.classification_augmenter(
            labeled_images, training=False
        )
        features = self.encoder(preprocessed_images, training=False)
        class_logits = self.linear_probe(features, training=False)
        probe_loss = self.probe_loss(labels, class_logits)

        self.probe_accuracy.update_state(labels, class_logits)
        return {"p_loss": probe_loss, "p_acc": self.probe_accuracy.result()}


# the contrastive model is pretrained for half of the epochs
pretraining_model = ContrastiveModel(width, temperature)
pretraining_model.compile(
    contrastive_optimizer=keras.optimizers.Adam(),
    probe_optimizer=keras.optimizers.Adam(),
)

pretraining_history = pretraining_model.fit(
    train_dataset, epochs=num_epochs // 2, validation_data=test_dataset
)
print(
    "Maximal validation accuracy: {:.2f}%".format(
        max(pretraining_history.history["val_p_acc"]) * 100
    )
)

"""
## Supervised finetuning of the pretrained encoder

We then finetune the encoder on the labeled examples for 30 epochs, by attaching a single
randomly initalized fully connected classification layer on its top.
"""

# the contrastive model is then finetuned for the other half of the epochs
finetuning_model = keras.Sequential(
    [
        layers.Input(shape=(96, 96, 3)),
        get_classification_augmenter(),
        pretraining_model.encoder,
        layers.Dense(10),
    ],
    name="pretrained_model",
)
finetuning_model.compile(
    optimizer=keras.optimizers.Adam(),
    loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=[keras.metrics.SparseCategoricalAccuracy(name="acc")],
)

finetuning_history = finetuning_model.fit(
    labeled_train_dataset, epochs=num_epochs // 2, validation_data=test_dataset
)
print(
    "Maximal validation accuracy: {:.2f}%".format(
        max(finetuning_history.history["val_acc"]) * 100
    )
)

"""
## Comparison against the baseline
"""

# the classification accuracies of the baseline and the pretraining + finetuning process:
def plot_training_curves(pretraining_history, finetuning_history, baseline_history):
    pretraining_epochs = len(pretraining_history.history["val_p_acc"])
    finetuning_epochs = len(finetuning_history.history["val_acc"])

    plt.figure(figsize=(8, 5), dpi=100)
    plt.plot(
        baseline_history.history["val_acc"],
        label="supervised baseline with random init",
    )
    plt.plot(
        pretraining_history.history["val_p_acc"], label="self-supervised pretraining"
    )
    plt.plot(
        list(range(pretraining_epochs, pretraining_epochs + finetuning_epochs)),
        finetuning_history.history["val_acc"],
        label="supervised finetuning",
    )
    plt.legend()
    plt.title("Classification accuracy during training")
    plt.xlabel("epochs")
    plt.ylabel("validation accuracy")

    plt.figure(figsize=(8, 5), dpi=100)
    plt.plot(
        baseline_history.history["val_loss"],
        label="supervised baseline with random init",
    )
    plt.plot(
        pretraining_history.history["val_p_loss"], label="self-supervised pretraining"
    )
    plt.plot(
        list(range(pretraining_epochs, pretraining_epochs + finetuning_epochs)),
        finetuning_history.history["val_loss"],
        label="supervised finetuning",
    )
    plt.legend()
    plt.title("Classification loss during training")
    plt.xlabel("epochs")
    plt.ylabel("validation loss")


plot_training_curves(pretraining_history, finetuning_history, baseline_history)

"""
By comparing the training curves, we can see that by using contrastive pretraining, a
higher validation accuracy can be reached, paired with a significantly lower validation
loss, which means that the pretrained network was able to generalize better when seeing
only a small amount of labeled examples.
"""

"""
## Improving further

### Architecture:

It is shown in the original paper, that increasing the width and depth of the models
improves performance with a higher rate then for supervised learning. Also, using a
[ResNet50](https://keras.io/api/applications/resnet/#resnet50-function) encoder is quite
standard in the literature. However keep in mind, that more powerful models will require
more memory and will limit the maximal batch size you can use.

It has [been](https://arxiv.org/abs/1905.09272)
[reported](https://arxiv.org/abs/1911.05722) that the usage of BatchNorm layers could
sometimes degrade performance, as it introduces an intra-batch dependency between
samples, which is why I did not have used them in this example. In my experiments
however, using BatchNorm, especially in the projection head, improves performance.

### Hyperparameters:

The hyperparameters of this example have been tuned manually for this task and
architecture, so without changing those, only marginal gains can be expected from further
hyperparameter tuning.

However for a different task or model architecture these would need tuning, so here are
my notes on the most important ones:
- **batch size**: since the objective can be interpreted as a classification over a batch
of images (loosely speaking), batch size is actually a more important hyperparameter than
usual. The higher, the better.
- **temperature**: the temperature defines "softness" of the of the softmax distibution
that is used in the cross-entropy loss, and is an important hyperparameter. Lower values
generally lead to a higher contrastive accuracy. A recent trick (in
[ALIGN](https://arxiv.org/pdf/2102.05918.pdf)) is to learn the temperature's value as
well (which can be done by defining it as a tf.Variable, and applying gradients on it).
This provides a good baseline value, however in my experiments the learned temperature
was somewhat lower than optimal, as it is optimized w.r.t. the contrastive loss, which is
not a perfect proxy for representation quality.
- **image augmentation strength**: stronger augmentations increase the difficulty of the
task, however after a point too strong augmentations will degrade performance.
- **learning rate schedule**: a constant schedule is used here, however it is quite
common in the literature to use a [cosine decay
schedule](https://www.tensorflow.org/api_docs/python/tf/keras/experimental/CosineDecay),
which can further improve performance.
- **optimizer**: Adam is used in this example, as it provides good performance with
default parameters. SGD with momentum requires more tuning, however it could slightly
increase performance.
"""

"""
## Related works

Other instance-level (image-level) contrastive learning methods:
- [MoCo](https://arxiv.org/abs/1911.05722) ([v2](https://arxiv.org/abs/2003.04297),
[v3](https://arxiv.org/abs/2104.02057)): uses a momentum-encoder as well, whose weights
are an exponential moving average of the target encoder
- [SwAV](https://arxiv.org/abs/2006.09882): uses clustering instead of pairwise comparison
- [BarlowTwins](https://arxiv.org/abs/2103.03230): uses a cross correlation-based
objective instead of pairwise comparison

I have implemented **MoCo** and **BarlowTwins** as well in a similar fashion, you can
find these three implementations together in [this
repository](https://github.com/beresandras/contrastive-classification-keras). A Colab
Notebook is included as well.

There is also a new line of works, which optimize a similar objective, however without
the use of any negatives:
- [BYOL](https://arxiv.org/abs/2006.07733): momentum-encoder + no negatives
- [SimSiam](https://arxiv.org/abs/2011.10566): no momentum-encoder + no negatives

In my experience these methods are more brittle (they can collapse to a constant
representation, I could not get them to work using this simple encoder architecture).
They are more dependent on the
[model](https://generallyintelligent.ai/understanding-self-supervised-contrastive-learning.html)
[architecture](https://arxiv.org/abs/2010.10241), however they improve performance
at smaller batch sizes.
"""
