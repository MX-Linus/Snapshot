"""
**Author:** [lukewood](https://twitter.com/luke_wood_ml)<br>
**Date created:** 2023/04/03<br>
**Last modified:** 2023/04/03<br>
**Description:** Use KerasCV to assemble object detection pipelines.

KerasCV offers a complete set of production grade APIs to solve object detection
problems.
These APIs include object detection specific
data augmentation techniques, Keras native COCO metrics, bounding box format
conversion utilities, visualization tools, pretrained object detection models,
and everything you need to train your own state of the art object detection
models!

Let's give KerasCV's object detection API a spin.
"""

"""shell
!pip install --upgrade keras-cv
"""

import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow import keras
from tensorflow.keras import optimizers
import keras_cv
import numpy as np
from keras_cv import bounding_box
import os
import resource
from keras_cv import visualization
import tqdm

"""
## API Introduction

Object detection is typically defined as the process of identifying, classifying,
and localizing objects within a given image.


In the modern era following the invention of *You Only Look Once* (aka YOLO),
object detection is typically solved using deep learning.
Most deep learning architectures do this by cleverly framing the object detection
problem as a combination of many small classification problems as well as
many regression problems.
This is done by generating many boxes of varying shapes and sizes across the
input images and assigning them each a class label, as well as
`x`, `y`, `width` and `height` offsets.
The model is trained to predict the class labels of each box, as well as the
`x`, `y`, `width`, and `height` offsets of each box that is predicted to be an
object.

# TODO anchor box image!!!!!!

Objection detection is a technically complex problem but we offer a
bulletproof approach to getting great results. Let's do this!

## Perform Detections with a Pretrained Model

![](https://storage.googleapis.com/keras-nlp/getting_started_guide/prof_keras_beginner.png)

The highest level API in the KerasCV API is the `keras_cv.models` API.
This API includes fully pretrained object detection models, such as
`keras_cv.models.RetinaNet`.

Let's get started by constructing a RetinaNet pretrained on the `pascalvoc`
dataset.
"""

model = keras_cv.models.RetinaNet.from_preset(
    "retinanet_resnet50_pascalvoc", bounding_box_format="xywh"
)

"""
Notice the `bounding_box_format` argument.
This is a critical piece of the KerasCV object detection API.
Every component that is to process bounding boxes accepts a required
`bounding_box_format` argument.
This is done to ensure that code remains readable, reusable, and clear.
Box format conversion bugs are perhaps the most common bug surface in object
detection pipelines - by requiring this parameter we mitigate against these
bugs (especially when combining code from many sources).

Next lets load an image:
"""

filepath = tf.keras.utils.get_file(origin="https://i.imgur.com/gCNcJJI.jpg")
image = keras.utils.load_img(filepath)
image = np.array(image)

visualization.plot_image_gallery(
    [image],
    value_range=(0, 255),
    rows=1,
    cols=1,
    scale=5,
)

"""
In order to use the `RetinaNet` architecture, you'll need to resize your image
to a size that is divisible by 64.
In object detection, the approach to resizing images to comply
with this constraint is *extremely* important.  If the resize operation distorts
the input's aspect ratio, the model will perform signficantly poorer.  For the
pretrained `"retinanet_resnet50_pascalvoc"` preset we are using, the final
`MeanAveragePrecision` on the `pascalvoc/2012` evaluation set drops to `0.15`
from `0.33` when using a naive resizing operation.

Additionally, if you crop to preserve the aspect ratio as you do in classification
your model may entirely miss some bounding boxes.  As such, when running inference
on an object detection model we recommend the use of padding to the desired size,
while resizing the longest size to match the aspect ration

KerasCV makes resizing properly easy; simply pass `pad_to_aspect_ratio=True` to
a `keras_cv.layers.Resizing` layer.

This can be implemented in one line of code:
"""

inference_resizing = keras_cv.layers.Resizing(
    640, 640, pad_to_aspect_ratio=True, bounding_box_format="xywh"
)
"""
This can be used as our inference preprocessing pipeline:
"""
image_batch = inference_resizing([image])

"""
`keras_cv.visualization.plot_bounding_box_gallery()` supports a `class_mapping`
parameter to highlight what class each box was assigned to.  Lets assemble a
class mapping now.
"""

class_ids = [
    "Aeroplane",
    "Bicycle",
    "Bird",
    "Boat",
    "Bottle",
    "Bus",
    "Car",
    "Cat",
    "Chair",
    "Cow",
    "Dining Table",
    "Dog",
    "Horse",
    "Motorbike",
    "Person",
    "Potted Plant",
    "Sheep",
    "Sofa",
    "Train",
    "Tvmonitor",
    "Total",
]
class_mapping = dict(zip(range(len(class_ids)), class_ids))


"""
Just like any other `keras.Model` you can predict bounding boxes using the
`model.predict()` API.
"""
y_pred = model.predict(image_batch)
visualization.plot_bounding_box_gallery(
    image_batch,
    value_range=(0, 255),
    rows=1,
    cols=1,
    y_pred=y_pred,
    scale=5,
    bounding_box_format="xywh",
    class_mapping=class_mapping,
)

"""
In order to support easy this easy and intuitive inference workflow, KerasCV
perform non-max suppression inside of the `RetinaNet` class.

In most cases you will want to customize the settings of your model's non-max
suppression operation.
This can be done by writing to the `model.prediction_decoder` attribute.

Let's use a customized `keras_cv.layers.MultiClassNonMaxSuppression` instance
to perform prediction decoding in our pretrained model.
In this case, we will tune the `iou_threshold` to `0.35`, and the
`confidence_threshold` to `0.75`.
"""

prediction_decoder = keras_cv.layers.MultiClassNonMaxSuppression(
    bounding_box_format="xywh",
    from_logits=True,
    # Decrease the required threshold to make predictions get pruned out
    iou_threshold=0.35,
    # Tune confidence threshold for predictions to pass NMS
    confidence_threshold=0.75,
)
model.prediction_decoder = prediction_decoder

y_pred = model.predict(image_batch)
visualization.plot_bounding_box_gallery(
    image_batch,
    value_range=(0, 255),
    rows=1,
    cols=1,
    y_pred=y_pred,
    scale=5,
    bounding_box_format="xywh",
    class_mapping=class_mapping,
)

"""
Looks great!
Up next, we'll take you through the process of training your own `KerasCV`
object detection model.
"""

"""

## Train a Custom Object Detection Model

![](https://storage.googleapis.com/keras-nlp/getting_started_guide/prof_keras_advanced.png)

Whether you're an object detection amateur or a well seasoned veteran, assembling
an object detection pipeline from scratch is a massive undertaking.
The most commonly used object detection solutions, such as `ultralytrics`'s
YOLO implementations, primarily rely on a bespoke single pipeline.
Extracting pieces of their code and re-using them yourself is a huge undertaking.

Luckily, all KerasCV object detection APIs are built as modular components.
Whether you need a complete pipeline, an object detection pipeline, or even just
a conversion utility to transform your boxes from `xywh` format to `xyxy`,
KerasCV has you covered.

In this guide, we'll assemble a full training pipeline for a KerasCV object
detection model.  This includes data loading, augmentation, metric evaluation,
and inference!

To get started, let's sort out all of our imports and define global
configuration parameters.
"""

BATCH_SIZE = 4
low, high = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (high, high))

"""
## Data loading

To get started, let's discuss data loading and bounding box formatting.
KerasCV has a predefined specificication for bounding boxes.
To comply with this, you
should package your bounding boxes into a dictionary matching the
specification below:

```
bounding_boxes = {
    # num_boxes may be a Ragged dimension
    'boxes': Tensor(shape=[batch, num_boxes, 4]),
    'classes': Tensor(shape=[batch, num_boxes])
}
```

`bounding_boxes['boxes']` contains the coordinates of your bounding box in a KerasCV
supported `bounding_box_format`.
KerasCV requires a `bounding_box_format` argument in all components that process
bounding boxes.
This is done to maximize your ability to plug and play individual components
into their object detection pipelines, as well as to make code self-documenting
across object detection pipelines.

To match the KerasCV API style, it is recommended that when writing a
custom data loader, you also support a `bounding_box_format` argument.
This makes it clear to those invoking your data loader what format the bounding boxes
are in.
In this example, we format our boxes to `xywh` format.

For example:

```python
train_ds, ds_info = your_data_loader.load(
    split='train', bounding_box_format='xywh', batch_size=8
)
```

Clearly yields bounding boxes in the format `xywh`.  You can read more about
KerasCV bounding box formats [in the API docs](https://keras.io/api/keras_cv/bounding_box/formats/).

Our data comesloaded into the format
`{"images": images, "bounding_boxes": bounding_boxes}`.  This format is
supported in all KerasCV preprocessing components.

Let's load some data and verify that our data looks as we expect it to.
"""


def unpackage_raw_tfds_inputs(inputs, bounding_box_format):
    image = inputs["image"]
    boxes = keras_cv.bounding_box.convert_format(
        inputs["objects"]["bbox"],
        images=image,
        source="rel_yxyx",
        target=bounding_box_format,
    )
    bounding_boxes = {
        "classes": tf.cast(inputs["objects"]["label"], dtype=tf.float32),
        "boxes": tf.cast(boxes, dtype=tf.float32),
    }
    return {"images": tf.cast(image, tf.float32), "bounding_boxes": bounding_boxes}


def load_pascal_voc(split, dataset, bounding_box_format):
    ds = tfds.load(dataset, split=split, with_info=False, shuffle_files=True)
    ds = ds.map(
        lambda x: unpackage_raw_tfds_inputs(x, bounding_box_format=bounding_box_format),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    return ds


train_ds = load_pascal_voc(
    split="train", dataset="voc/2007", bounding_box_format="xywh"
)
eval_ds = load_pascal_voc(split="test", dataset="voc/2007", bounding_box_format="xywh")
eval_ds = load_pascal_voc(dataset="voc/2007", split="test", bounding_box_format="xywh")

train_ds = train_ds.shuffle(BATCH_SIZE * 4)
visualization.visualize_dataset(train_ds, value_range=(0, 255), rows=2, cols=2)
"""
Next, lets batch our data.

In KerasCV object detection tasks it is recommended that
users use ragged batches of inputs.
This is due to the fact that images may be of different sizes in PascalVOC,
as well as the fact that there may be different numbers of bounding boxes per
image.

To construct a ragged dataset in a `tf.data` pipeline, you can use the
`ragged_batch()` method.
"""

train_ds = train_ds.ragged_batch(BATCH_SIZE, drop_remainder=True)
eval_ds = eval_ds.ragged_batch(BATCH_SIZE, drop_remainder=True)

"""
Let's make sure our dataset is following the format KerasCV expects.
By using the `visualization.visualize_dataset()` API, you can visually verify
that your data is in the format that KerasCV expects.  If the bounding boxes
are not drawn on, or are drawn in the wrong locations that is a sign that your
data is mis-formatted.
"""

visualization.visualize_dataset(train_ds, bounding_box_format="xywh")

"""
And for the eval set:
"""

visualization.visualize_dataset(eval_ds, bounding_box_format="xywh")

"""
If you are not running your experiment on a local machine, you can also make
`visualize_dataset()` dump the plot to a file using the `path` parameter:
"""
visualization.visualize_dataset(eval_ds, bounding_box_format="xywh", path="eval.png")

"""
Looks like everything is structured as expected.
Now we can move on to constructing our
data augmentation pipeline.

## Data augmentation

One of the most labor-intensive tasks when constructing object detection
pipelines is data augmentation.  Image augmentation techniques must be aware of the underlying
bounding boxes, and must update them accordingly.

Luckily, KerasCV natively supports bounding box augmentation with its extensive
library
of [data augmentation layers](https://keras.io/api/keras_cv/layers/preprocessing/).
The code below loads the Pascal VOC dataset, and performs on-the-fly bounding box
friendly data augmentation inside of a `tf.data` pipeline.
"""

augmenter = keras.Sequential(
    layers=[
        keras_cv.layers.RandAugment(
            augmentations_per_image=1, rate=0.5, magnitude=0.3, geometric=False
        ),
        keras_cv.layers.RandomFlip(mode="horizontal", bounding_box_format="xywh"),
        keras_cv.layers.JitteredResize(
            target_size=(640, 640), scale_factor=(0.75, 1.3), bounding_box_format="xywh"
        ),
    ]
)

train_ds = train_ds.map(augmenter, num_parallel_calls=tf.data.AUTOTUNE)
"""
Let's make sure our augmentations look how we expect them to:
"""
visualize_dataset(train_ds, bounding_box_format="xywh")

"""
Great!  We now have a bounding box friendly data augmentation pipeline.
Let's format our evaluation dataset to match.  Instead of using
`JitteredResize`, let's use the deterministic `keras_cv.layers.Resizing()`
layer.
"""

inference_resizing = keras_cv.layers.Resizing(
    640, 640, bounding_box_format="xywh", pad_to_aspect_ratio=True
)
eval_ds = eval_ds.map(inference_resizing, num_parallel_calls=tf.data.AUTOTUNE)

"""
Due to the fact that the resize operation differs between the train dataset,
which uses `JitteredResize()` to resize images, and the inference dataset which
uses `layers.Resizing(pad_to_aspect_ratio=True)`, it is good practice to
visualize both datasets:
"""

visualize_dataset(eval_ds, bounding_box_format="xywh")

"""
Finally, let's unpackage our inputs from the preprocessing dictionary, and
prepare to feed the inputs into our model.  In order to be TPU compatible,
bounding box Tensors need to be `Dense` instead of `Ragged`.  If training on
GPU, you can omit the `bounding_box.to_dense()` call.  If ommitted,
the KerasCV RetinaNet
label encoder will automatically correctly encode Ragged training targets.
"""


def dict_to_tuple(inputs):
    return inputs["images"], bounding_box.to_dense(
        inputs["bounding_boxes"], max_boxes=32
    )


train_ds = train_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
eval_ds = eval_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)

train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
eval_ds = eval_ds.prefetch(tf.data.AUTOTUNE)

"""
Our data pipeline is now complete!
We can now move on to model creation and training.

### Model creation

We'll use the KerasCV API to construct a RetinaNet model.
In this tutorial we use a pretrained ResNet50 backbone, initializing the
weights to weights produced by training a classification model on the imagenet
dataset.

KerasCV makes it easy to construct a `RetinaNet` with any of the KerasCV
backbones.  Simply use one of the presets for the architecture you'd like!

For example:
"""

model = keras_cv.models.RetinaNet.from_preset(
    "resnet50_v2_imagenet",
    # number of classes to be used in box classification
    num_classes=len(class_mapping) + 1,
    # For more info on supported bounding box formats, visit
    # https://keras.io/api/keras_cv/bounding_box/
    bounding_box_format="xywh",
)

"""
That is all it takes to construct a KerasCV RetinaNet.  The RetinaNet accepts
tuples of dense image Tensors and bounding box dictionaries to `fit()` and
`train_on_batch()`

This matches what we have constructed in our input pipeline above.
"""

"""
### Optimizer

Next, let's construct a learning rate schedule and optimizer for our model.
"""
base_lr = 0.005 * (BATCH_SIZE / 16)
lr_decay = tf.keras.optimizers.schedules.PiecewiseConstantDecay(
    boundaries=[12000 * 16, 16000 * 16],
    values=[base_lr, 0.1 * base_lr, 0.01 * base_lr],
)

# including a global_clipnorm is extremely important in object detection tasks
optimizer = tf.keras.optimizers.SGD(
    learning_rate=lr_decay, momentum=0.9, global_clipnorm=10.0
)

"""
**Note: be sure to freeze BatchNormalization layers***

And important but easy to miss step in training your own object detection model
is freezing the `BatchNormalization` layers in your backbone.
We felt it was a violation of user expectations to automatically do this,
so instead we recommend you do it in your training loops.
"""

for layer in model.backbone.layers:
    if isinstance(layer, keras.layers.BatchNormalization):
        layer.trainable = False

"""
### Metric Evaluation

Just like any other metric, you can pass the `KerasCV` object detection metrics
to `compile()`.  The most popular Object Detection metrics are COCO metrics,
which were published alongside the MSCOCO dataset.  KerasCV provides an easy
to use suite of COCO metrics. under the `keras_cv.metrics.BoxCOCOMetrics`
symbol:
"""
coco_metrics = keras_cv.metrics.BoxCOCOMetrics(
    bounding_box_format="xywh", evaluate_freq=128
)
"""
Due to the high computational cost of computing COCO metrics, the KerasCV
`BoxCOCOMetrics` component requires an `evaluate_freq` parameter to be passed to
its constructor.  Every `evaluate_freq`-th call to `update_state()`, the metric
will recompute the result.  In between invocations, a cached version of the
result will be returned.

To force an evaluation, you may call `coco_metrics.result(force=True)`:
"""
model.compile(
    classification_loss="focal",
    box_loss="smoothl1",
    optimizer=optimizer,
    metrics=[coco_metrics],
)
result = model.evaluate(eval_ds)
result = coco_metrics.result(force=True)
print(tablify(result))

"""
**A note on TPU compatibility**

Evaluation of `BoxCOCOMetrics` require running `tf.image.non_max_suppression()`
inside of the `model.train_step()` and `model.evaluation_step()` functions.
Due to this, the metric suite is not compatible with TPU when used with the
`compile()` API.

Luckily, there are two workarounds that allow you to still train a RetinaNet on TPU:

- The use of a custom callback
- Using a [SideCarEvaluator](https://www.tensorflow.org/api_docs/python/tf/keras/utils/SidecarEvaluator)

Let's use a custom callback to achieve TPU compatibility in this guide:
"""


class EvaluateCOCOMetricsCallback(keras.callbacks.Callback):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.metrics = keras_cv.metrics.BoxCOCOMetrics(
            bounding_box_format="xywh",
            # passing 1e9 ensures we never evaluate until
            # `metrics.result(force=True)` is
            # called.
            evaluate_freq=1e9,
        )

    def on_epoch_end(self, epoch, logs):
        self.metrics.reset_state()
        for batch in tqdm.tqdm(self.data):
            images, y_true = batch[0], batch[1]
            y_pred = self.model.predict(images, verbose=0)
            self.metrics.update_state(y_true, y_pred)

        metrics = self.metrics.result()
        logs.update(metrics)
        return logs


"""
## Training our model

All that is left to do is train our model.  KerasCV object detection models follow the
standard Keras workflow, leveraging `compile()` and `fit()`.

Let's compile our model:
"""

model.compile(
    classification_loss="focal",
    box_loss="smoothl1",
    optimizer=optimizer,
    # We will use our custom callback to evaluate COCO metrics
    metrics=None,
)

"""
And run `model.fit()`!
"""

# If you want to train the fully model, uncomment `.take(20)` from each
# of the following dataset references.

model.fit(
    train_ds.take(20),
    validation_data=eval_ds.take(20),
    # Run for 10-35~ epochs to achieve good scores.
    epochs=1,
    callbacks=[EvaluateCOCOMetricsCallback(eval_ds.take(20))],
)

"""
To achieve reasonable scores, you will want to run `fit()` with 10-35~ epochs.
"""

"""
Visualizing
"""

"""
This metric can be used with `fit()` like any other callback, simply pass:
`callbacks=callbacks + [EvaluateMetricsCallback(data=eval_ds)]` to your `fit()` call.

## Inference and Plotting results

KerasCV makes object detection inference simple.  `model.predict(images)` returns a
RaggedTensor of bounding boxes.  By default, `RetinaNet.predict()` will perform
a non max suppression operation for you.

In this section, we will use a `keras_cv` provided preset:
"""
model = keras_cv.models.RetinaNet.from_preset(
    "retinanet_resnet50_pascalvoc", bounding_box_format="xywh"
)

"""
And construct a basic helper function to plot our results:
"""


def visualize_detections(model, dataset, bounding_box_format):
    images, y_true = next(iter(dataset.shuffle(8).take(1)))
    y_pred = model.predict(images)
    y_pred = bounding_box.to_ragged(y_pred)
    visualization.plot_bounding_box_gallery(
        images,
        value_range=(0, 255),
        bounding_box_format=bounding_box_format,
        y_true=y_true,
        y_pred=y_pred,
        scale=3,
        rows=2,
        cols=4,
        show=True,
        font_scale=1,
        class_mapping=class_mapping,
    )


visualize_detections(model, bounding_box_format="xywh")

"""
To achieve good visual results, you may want to grid-search prediction decoders
until you find a configuration that achieves a strong `MeanAveragePrecision`.

Luckily, with KerasCV this is easy:
"""

best_decoder = None
score_to_beat = 0
worst_score = 1.0

iou_thresholds = [0.35, 0.5, 0.65]
confidence_thresholds = [0.5, 0.75, 0.9]
for iou_threshold in tqdm(iou_thresholds):
    for confidence_threshold in confidence_thresholds:
        coco_metrics.reset_state()
        prediction_decoder = keras_cv.layers.MultiClassNonMaxSuppression(
            bounding_box_format="xywh",
            from_logits=True,
            # Decrease the required threshold to make predictions get pruned out
            iou_threshold=iou_threshold,
            # Tune confidence threshold for predictions to pass NMS
            confidence_threshold=iou_threshold,
        )
        model.prediction_decoder = prediction_decoder

        # Remove take(20) in a production setting
        coco_metrics.reset_state()
        model.evaluate(eval_ds.take(20))
        result = coco_metrics.result(force=True)
        if result["MaP"] > score_to_beat:
            best_decoder = prediction_decoder
            score_to_beat = result["MaP"]

        if result["MaP"] < worst_score:
            worst_score = result["MaP"]

model.prediction_decoder = best_decoder
print(
    f"Best scores found with iou_threshold={best_decoder.iou_threshold},
    f"confidence_threshold={best_decoder.confidence_threshold}. Best MaP is "
    f"{score_to_beat}, worst MaP is {worst_score}."
)

"""
Lets visualize the results using our optimal decoder:
"""

visualize_detections(model, bounding_box_format="xywh", dataset=eval_ds.shuffle(8))

"""
Awesome!

One final helpful pattern to be aware of is monitoring training is to visualize
detections in a `keras.callbacks.Callback`:
"""


class VisualizeDetections(keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs):
        visualize_detections(self.model, eval_ds, bounding_box_format="xywh")


"""
## Takeaways and Next Steps

KerasCV makes it easy to construct state-of-the-art object detection pipelines.
In this guide, we started off by writing a data loader using the KerasCV
bounding box specification.
Following this, we assembled a production grade data augmentation pipeline using
the module `KerasCV` preprocessing layers in <50 lines of code.
We constructed a RetinaNet and trained for an epoch.

KerasCV object detection components can be used independently, but also have deep
integration with each other.
KerasCV makes authoring production grade bounding box augmentation,
model training, visualization, and
metric evaluation easy.

Some follow up exercises for the reader:

- add additional augmentation techniques to improve model performance
- tune the hyperparameters and data augmentation used to produce high quality results
- train an object detection model on your own dataset

One last fun code snippet to showcase the power of KerasCV's modular API!
"""
images = stable_diffusion.text_to_image(
    "A photograph of a cool looking cat sitting on the beach.", batch_size=4, seed=1337
)
y_pred = model.predict(images)
visualization.plot_bounding_box_gallery(
    images,
    value_range=(0, 255),
    rows=2,
    cols=2,
    scale=5,
    bounding_box_format="xywh",
    class_mapping=class_mapping,
)
