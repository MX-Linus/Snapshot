"""
Title: Train an Object Detection Model on Pascal VOC 2007 using KerasCV
Author: [lukewood](https://lukewood.xyz)
Date created: 2022/08/22
Last modified: 2022/08/22
Description: Use KerasCV to train a RetinaNet on Pascal VOC 2007.
"""

"""
## Overview

KerasCV offers a complete set of APIs to train your own state-of-the-art,
production-grade object detection model.  These APIs include object detection specific
data augmentation techniques, models, and COCO metrics.

To get started, let's sort out all of our imports and define global configuration parameters.
"""

import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow import keras
from tensorflow.keras import optimizers

import keras_cv
from keras_cv import bounding_box
import os

BATCH_SIZE = 8
EPOCHS = 100
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "checkpoint")

"""
## Data loading

In this guide, we use the data-loading function: `keras_cv.datasets.pascal_voc.load()`.
KerasCV supports a `bounding_box_format` argument in all components that process
bounding boxes.  To match the KerasCV API style, it is recommended that when writing a
custom data loader, you also support a `bounding_box_format` argument.
This makes it clear to those invoking your data loader what format the bounding boxes
are in.

For example:

```python
train_ds, ds_info = keras_cv.datasets.pascal_voc.load(
    split='train', bounding_box_format='xywh', batch_size=8
)
```

Clearly yields bounding boxes in the format `xywh`.  You can read more about
KerasCV bounding box formats [in the API docs](https://keras.io/api/keras_cv/bounding_box/formats/).

Our data comesloaded into the format
`{"images": images, "bounding_boxes": bounding_boxes}`.  This format is supported in all
KerasCV preprocessing components.

Let's load some data and verify that our data looks as we expect it to.
"""

dataset, dataset_info = keras_cv.datasets.pascal_voc.load(
    split="train", bounding_box_format="xywh", batch_size=9
)


def visualize_dataset(dataset, bounding_box_format):
    color = tf.constant(((255.0, 0, 0),))
    plt.figure(figsize=(10, 10))
    for i, example in enumerate(dataset.take(9)):
        images, boxes = example["images"], example["bounding_boxes"]
        boxes = keras_cv.bounding_box.convert_format(
            boxes, source=bounding_box_format, target="rel_yxyx", images=images
        )
        boxes = boxes.to_tensor(default_value=-1)
        plotted_images = tf.image.draw_bounding_boxes(images, boxes[..., :4], color)
        plt.subplot(9 // 3, 9 // 3, i + 1)
        plt.imshow(plotted_images[0].numpy().astype("uint8"))
        plt.axis("off")
    plt.show()


visualize_dataset(dataset, bounding_box_format="xywh")

"""
Looks like everything is structured as expected.  Now we can move on to constructing our
data augmentation pipeline.
"""

"""
## Data augmentation

One of the most labor-intensive tasks when constructing object detection pipelines is
data augmentation.  Image augmentation techniques must be aware of the underlying
bounding boxes, and must update them accordingly.

Luckily, KerasCV natively supports bounding box augmentation with its extensive library
of [data augmentation layers](https://keras.io/api/keras_cv/layers/preprocessing/).
The code below loads the Pascal VOC dataset, and performs on-the-fly bounding box
friendly data augmentation inside of a `tf.data` pipeline.
"""

# train_ds is batched as a (images, bounding_boxes) tuple
# bounding_boxes are ragged
train_ds, train_dataset_info = keras_cv.datasets.pascal_voc.load(
    bounding_box_format="xywh", split="train", batch_size=BATCH_SIZE
)
val_ds, val_dataset_info = keras_cv.datasets.pascal_voc.load(
    bounding_box_format="xywh", split="validation", batch_size=BATCH_SIZE
)

augmenter = keras_cv.layers.RandomChoice(
    layers=[
        keras_cv.layers.RandomFlip(mode="horizontal", bounding_box_format="xywh"),
        keras_cv.layers.RandomColorJitter(
            value_range=(0, 255),
            brightness_factor=0.1,
            contrast_factor=0.1,
            saturation_factor=0.1,
            hue_factor=0.1,
        ),
        keras_cv.layers.RandomSharpness(value_range=(0, 255), factor=0.1),
    ]
)

# train_ds = train_ds.map(augmenter, num_parallel_calls=tf.data.AUTOTUNE)
visualize_dataset(train_ds, bounding_box_format="xywh")

"""
Great!  We now have a bounding box friendly augmentation pipeline.

Next, let's unpackage our inputs from the preprocessing dictionary, and prepare to feed
the inputs into our model.
"""


def dict_to_tuple(inputs):
    return inputs["images"], inputs["bounding_boxes"]


train_ds = train_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
val_ds = val_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)

train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
val_ds = val_ds.prefetch(tf.data.AUTOTUNE)

"""
Our data pipeline is now complete.  We can now move on to model creation and training.
"""

"""
## Model creation

We'll use the KerasCV API to construct a RetinaNet model.  In this tutorial we use
a pretrained ResNet50 backbone using weights.  In order to perform fine-tuning, we
freeze the backbone before training.  When `include_rescaling=True` is set, inputs to
the model are expected to be in the range `[0, 255]`.
"""

model = keras_cv.models.RetinaNet(
    # number of classes to be used in box classification
    classes=20,
    # For more info on supported bounding box formats, visit
    # https://keras.io/api/keras_cv/bounding_box/
    bounding_box_format="xywh",
    # KerasCV offers a set of pre-configured backbones
    backbone="resnet50",
    # Each backbone comes with multiple pre-trained weights
    # These weights match the weights available in the `keras_cv.model` class.
    backbone_weights="imagenet",
    # include_rescaling tells the model whether your input images are in the default
    # pixel range (0, 255) or if you have already rescaled your inputs to the range
    # (0, 1).  In our case, we feed our model images with inputs in the range (0, 255).
    include_rescaling=True,
)
# you can disable training of the backbone and only train the FPN
model.backbone.trainable = False

"""
That is all it takes to construct a KerasCV RetinaNet.  The RetinaNet accepts tuples of
dense image Tensors and ragged bounding box Tensors to `fit()` and `train_on_batch()`
This matches what we have constructed in our input pipeline above.

The RetinaNet `call()` method outputs two values: training targets and inference targets.
In this guide, we are primarily concerned with the inference targets.  Internally, the
training targets are used by `keras_cv.losses.ObjectDetectionLoss()` to train the
network.
"""

"""
## Training our model

All that is left to do is train our model.  KerasCV object detection models follow the
standard Keras workflow, leveraging `compile()` and `fit()`.

Let's compile our model:
"""


optimizer = optimizers.SGD(learning_rate=0.1, momentum=0.9, global_clipnorm=10.0)


# We scale FocalLoss as the loss output values from the classification loss tend to be
# much smaller than the values from the box loss.
class ScaledFocalLoss(keras_cv.losses.FocalLoss):
    def call(self, y_true, y_pred):
        return 50.0 * super().call(y_true, y_pred)


model.compile(
    classification_loss=ScaledFocalLoss(from_logits=True),
    box_loss=keras.losses.Huber(delta=1.0),
    optimizer=optimizer,
)

"""
All that is left to do is construct some callbacks:
"""

callbacks = [
    keras.callbacks.TensorBoard(log_dir="logs"),
    keras.callbacks.EarlyStopping(patience=15),
    keras.callbacks.ReduceLROnPlateau(patience=10),
    keras.callbacks.ModelCheckpoint(CHECKPOINT_PATH, save_weights_only=True),
]

"""
And run `model.fit()`!
"""

model.fit(
    train_ds,
    validation_data=val_ds.take(20),
    epochs=EPOCHS,
    callbacks=callbacks,
)

"""
An important nuance to note is that by default the KerasCV RetinaNet does not evaluate
metrics at train time.  This is to ensure optimal GPU performance and TPU compatibility.
If you want to evaluate train time metrics, you may pass
`evaluate_train_time_metrics=True` to the `keras_cv.models.RetinaNet` constructor.
"""

"""
## Evaluation with COCO Metrics

KerasCV offers a suite of in-graph COCO metrics that support batch-wise evaluation.
More information on these metrics is available in:

- [Efficient Graph-Friendly COCO Metric Computation for Train-Time Model Evaluation](https://arxiv.org/abs/2207.12120)
- [Using KerasCV COCO Metrics](https://keras.io/guides/keras_cv/coco_metrics/)

Let's construct two COCO metrics, an instance of
`keras_cv.metrics.COCOMeanAveragePrecision` with the parameterization to match the
standard COCO Mean Average Precision metric, and `keras_cv.metrics.COCORecall`
parameterized to match the standard COCO Recall metric.
"""

metrics = [
    keras_cv.metrics.COCOMeanAveragePrecision(
        class_ids=range(20),
        bounding_box_format="xywh",
        name="Mean Average Precision",
    ),
    keras_cv.metrics.COCORecall(
        class_ids=range(20),
        bounding_box_format="xywh",
        max_detections=100,
        name="Recall",
    ),
]


"""
Next, we can evaluate the metrics by re-compiling the model, and running
`model.evaluate()`:
"""

model.compile(
    metrics=metrics,
    box_loss=model.box_loss,
    classification_loss=model.classification_loss,
    optimizer=model.optimizer,
)
metrics = model.evaluate(val_ds.take(20), return_dict=True)
print(metrics)
# {"Mean Average Precision": 0.612, "Recall": 0.767}

"""
## Inference

KerasCV makes object detection inference simple.  `model.predict(images)` returns a
RaggedTensor of bounding boxes.  By default, `RetinaNet.predict()` will perform
a non max suppression operation for you.
"""

model = keras_cv.models.RetinaNet(
    classes=20,
    bounding_box_format="xywh",
    backbone="resnet50",
    backbone_weights="imagenet",
    include_rescaling=True,
)
model.load_weights(CHECKPOINT_PATH)


def visualize_detections(model):
    train_ds, val_dataset_info = keras_cv.datasets.pascal_voc.load(
        bounding_box_format="xywh", split="train", batch_size=9
    )
    train_ds = train_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
    images, labels = next(iter(train_ds.take(1)))
    predictions = model.predict(images)
    color = tf.constant(((255.0, 0, 0),))
    plt.figure(figsize=(10, 10))
    predictions = keras_cv.bounding_box.convert_format(
        predictions, source="xywh", target="rel_yxyx", images=images
    )
    predictions = predictions.to_tensor(default_value=-1)
    plotted_images = tf.image.draw_bounding_boxes(images, predictions[..., :4], color)
    for i in range(9):
        plt.subplot(9 // 3, 9 // 3, i + 1)
        plt.imshow(plotted_images[i].numpy().astype("uint8"))
        plt.axis("off")
    plt.savefig("test.png")


visualize_detections(model)

"""
To get good results, you should train for at least 50 epochs.  You may also need to
tune the prediction decoder layer.  This can be done by passing a custom prediction
decoder to the RetinaNet constructor as follows.
"""

prediction_decoder = keras_cv.layers.NmsPredictionDecoder(
    bounding_box_format="xywh",
    anchor_generator=keras_cv.models.RetinaNet.default_anchor_generator(
        bounding_box_format="xywh"
    ),
    suppression_layer=keras_cv.layers.NonMaxSuppression(
        bounding_box_format="xywh", classes=20, confidence_threshold=0.99
    ),
)
model = keras_cv.models.RetinaNet(
    classes=20,
    bounding_box_format="xywh",
    backbone="resnet50",
    backbone_weights="imagenet",
    include_rescaling=True,
    prediction_decoder=prediction_decoder,
)
model.load_weights(CHECKPOINT_PATH)
visualize_detections(model)

"""
## Results and conclusions

KerasCV makes it easy to construct state-of-the-art object detection pipelines.  All of
the KerasCV object detection components can be used independently, but also have deep
integration with each other.  With KerasCV, bounding box augmentation, train-time COCO
metrics evaluation, and more, are all made simple and consistent.

By default, this script runs for a single epoch.  To run training to convergence,
invoke the script with a command line flag `--epochs=500`.  To save you the effort of
running the script for 500 epochs, we have produced a Weights and Biases report covering
the training results below!  As a bonus, the report includes a training run with and
without data augmentation.

[Metrics from a 500 epoch Weights and Biases Run are available here](
    https://tinyurl.com/y34xx65w
)
"""
