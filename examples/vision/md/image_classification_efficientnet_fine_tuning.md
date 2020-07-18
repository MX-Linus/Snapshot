# Image classification via fine-tuning with EfficientNet

**Author:** [Yixing Fu](https://github.com/yixingfu)<br>
**Date created:** 2020/06/30<br>
**Last modified:** 2020/07/16<br>
**Description:** Use EfficientNet with weights pre-trained on imagenet for Stanford Dogs classification.


<img class="k-inline-icon" src="https://colab.research.google.com/img/colab_favicon.ico"/> [**View in Colab**](https://colab.research.google.com/github/keras-team/keras-io/blob/master/examples/vision/ipynb/image_classification_efficientnet_fine_tuning.ipynb)  <span class="k-dot">•</span><img class="k-inline-icon" src="https://github.com/favicon.ico"/> [**GitHub source**](https://github.com/keras-team/keras-io/blob/master/examples/vision/image_classification_efficientnet_fine_tuning.py)



---
## Introduction: what is EfficientNet

EfficientNet, first introduced in [Tan and Le, 2019](https://arxiv.org/abs/1905.11946)
is among the most efficient models (i.e. requiring least FLOPS for inference)
that reaches State-of-the-Art accuracy on both
imagenet and common image classification transfer learning tasks.

The smallest base model is similar to [MnasNet](https://arxiv.org/abs/1807.11626), which
reached near-SOTA with a significantly smaller model. By introducing a heuristic way to
scale the model, EfficientNet provides a family of models (B0 to B7) that represents a
good combination of efficiency and accuracy on a variety of scales. Such a scaling
heuristics (compound-scaling, details see
[Tan and Le, 2019](https://arxiv.org/abs/1905.11946)) allows the
efficiency-oriented base model (B0) to surpass models at every scale, while avoiding
extensive grid-search of hyperparameters.

A summary of the latest updates on the model is available at
[here](https://github.com/tensorflow/tpu/tree/master/models/official/efficientnet), where various
augmentation schemes and semi-supervised learning approaches are applied to further
improve the imagenet performance of the models. These extensions of the model can be used
by updating weights without changing model architecture.

---
## B0 to B7 variants of EfficientNet

*(This section provides some details on "compound scaling", and can be skipped
if you're only interested in using the models)*

Based on the [original paper](https://arxiv.org/abs/1905.11946) people may have the
impression that EfficientNet is a continuous family of models created by arbitrarily
choosing scaling factor in as Eq.(3) of the paper.  However, choice of resolution,
depth and width are also restricted by many factors:

- Resolution: Resolutions not divisible by 8, 16, etc. cause zero-padding near boundaries
of some layers which wastes computational resources. This especially applies to smaller
variants of the model, hence the input resolution for B0 and B1 are chosen as 224 and
240.

- Depth and width: The building blocks of EfficientNet demands channel size to be
multiples of 8.

- Resource limit: Memory limitation may bottleneck resolution when depth
and width can still increase. In such a situation, increasing depth and/or
width but keep resolution can still improve performance.

As a result, the depth, width and resolution of each variant of the EfficientNet models
are hand-picked and proven to produce good results, though they may be significantly
off from the compound scaling formula.
Therefore, the keras implementation (detailed below) only provide these 8 models, B0 to B7,
instead of allowing arbitray choice of width / depth / resolution parameters.

---
## Keras implementation of EfficientNet

An implementation of EfficientNet B0 to B7 has been shipped with tf.keras since TF2.3. To
use EfficientNetB0 for classifying 1000 classes of images from imagenet, run:

```python
from tensorflow.keras.applications import EfficientNetB0
model = EfficientNetB0(weights='imagenet')
```

This model takes input images of shape (224, 224, 3), and the input data should range
[0, 255]. Normalization is included as part of the model.

Because training EfficientNet on ImageNet takes a tremendous amount of resources and
several techniques that are not a part of the model architecture itself. Hence the Keras
implementation by default loads pre-trained weights obtained via training with
[AutoAugment](https://arxiv.org/abs/1805.09501).

For B0 to B7 base models, the input shapes are different. Here is a list of input shape
expected for each model:

| Base model | resolution|
|----------------|-----|
| EfficientNetB0 | 224 |
| EfficientNetB1 | 240 |
| EfficientNetB2 | 260 |
| EfficientNetB3 | 300 |
| EfficientNetB4 | 380 |
| EfficientNetB5 | 456 |
| EfficientNetB6 | 528 |
| EfficientNetB7 | 600 |

When the model is intended for transfer learning, the Keras implementation
provides a option to remove the top layers:
```
model = EfficientNetB0(include_top=False, weights='imagenet')
```
This option excludes the final `Dense` layer that turns 1280 features on the penultimate
layer into prediction of the 1000 ImageNet classes. Replacing the top layer with custom
layers allows using EfficientNet as a feature extractor in a transfer learning workflow.

Another argument in the model constructor worth noticing is `drop_connect_rate` which controls
the dropout rate responsible for [stochastic depth](https://arxiv.org/abs/1603.09382).
This parameter serves as a toggle for extra regularization in finetuning, but does not
affect loaded weights. For example, when stronger regularization is desired, try:

```python
model = EfficientNetB0(weights='imagenet', drop_connect_rate=0.4)
```
The default value is 0.2.

---
## Example: EfficientNetB0 for Stanford Dogs.

EfficientNet is capable of a wide range of image classification tasks.
This makes it a good model for transfer learning.
As an end-to-end example, we will show using pre-trained EfficientNetB0 on
[Stanford Dogs](http://vision.stanford.edu/aditya86/ImageNetDogs/main.html) dataset.


```python
# IMG_SIZE is determined by EfficientNet model choice
IMG_SIZE = 224
```

---
## Setup and data loading

This example requires TensorFlow 2.3 or above.

To use TPU, the TPU runtime must match current running TensorFlow
version. If there is a mismatch, try:

```python
from cloud_tpu_client import Client
c = Client()
c.configure_tpu_version(tf.__version__, restart_type="always")
```


```python
import tensorflow as tf

try:
    tpu = tf.distribute.cluster_resolver.TPUClusterResolver()  # TPU detection
    print("Running on TPU ", tpu.cluster_spec().as_dict()["worker"])
    tf.config.experimental_connect_to_cluster(tpu)
    tf.tpu.experimental.initialize_tpu_system(tpu)
    strategy = tf.distribute.experimental.TPUStrategy(tpu)
except ValueError:
    print("Not connected to a TPU runtime. Using CPU/GPU strategy")
    strategy = tf.distribute.MirroredStrategy()

```

<div class="k-default-codeblock">
```
Not connected to a TPU runtime. Using CPU/GPU strategy
INFO:tensorflow:Using MirroredStrategy with devices ('/job:localhost/replica:0/task:0/device:GPU:0',)

```
</div>
### Loading data

Here we load data from [tensorflow_datasets](https://www.tensorflow.org/datasets)
(hereafter TFDS).
Stanford Dogs dataset is provided in
TFDS as [stanford_dogs](https://www.tensorflow.org/datasets/catalog/stanford_dogs).
It features 20,580 images that belong to 120 classes of dog breeds
(12,000 for training and 8,580 for testing).

By simply changing `dataset_name` below, you may also try this notebook for
other datasets in TFDS such as
[cifar10](https://www.tensorflow.org/datasets/catalog/cifar10),
[cifar100](https://www.tensorflow.org/datasets/catalog/cifar100),
[food101](https://www.tensorflow.org/datasets/catalog/food101),
etc. When the images are much smaller than the size of EfficientNet input,
we can simply upsample the input images. It has been shown in
[Tan and Le, 2019](https://arxiv.org/abs/1905.11946) that transfer learning
result is better for increased resolution even if input images remain small.

For TPU: if using TFDS datasets,
a [GCS bucket](https://cloud.google.com/storage/docs/key-terms#buckets)
location is required to save the datasets. For example:

```python
tfds.load(dataset_name, data_dir="gs://example-bucket/datapath")
```

Also, both the current environment and the TPU service account have
proper [access](https://cloud.google.com/tpu/docs/storage-buckets#authorize_the_service_account)
to the bucket. Alternatively, for small datasets you may try loading data
into the memory and use `tf.data.Dataset.from_tensor_slices()`.


```python
import tensorflow_datasets as tfds

batch_size = 64

dataset_name = "stanford_dogs"
(ds_train, ds_test), ds_info = tfds.load(
    dataset_name, split=["train", "test"], with_info=True, as_supervised=True
)
NUM_CLASSES = ds_info.features["label"].num_classes

```

When the dataset include images with various size, we need to resize them into a
shared size. The Stanford Dogs dataset includes only images at least 200x200
pixels in size. Here we resize the images to the input size needed for EfficientNet.


```python
size = (IMG_SIZE, IMG_SIZE)
ds_train = ds_train.map(lambda image, label: (tf.image.resize(image, size), label))
ds_test = ds_test.map(lambda image, label: (tf.image.resize(image, size), label))
```

### Visualizing the data

The following code shows the first 9 images with their labels both
in numeric form and text.


```python
import matplotlib.pyplot as plt

label_info = ds_info.features["label"]
for i, (image, label) in enumerate(ds_train.take(9)):
    ax = plt.subplot(3, 3, i + 1)
    plt.imshow(image)
    plt.title("{}, {}".format((label), label_info.int2str(label)))
    plt.axis("off")

```

<div class="k-default-codeblock">
```
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
WARNING:matplotlib.image:Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).

```
</div>
![png](/img/examples/vision/image_classification_efficientnet_fine_tuning/image_classification_efficientnet_fine_tuning_10_1.png)


### Data augmentation

We can use preprocessing layers APIs for image augmentation.


```python
from tensorflow.keras.layers.experimental import preprocessing
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

img_augmentation = Sequential(
    [
        preprocessing.RandomRotation(factor=0.15),
        preprocessing.RandomTranslation(height_factor=0.1, width_factor=0.1),
        preprocessing.RandomFlip(),
        preprocessing.RandomContrast(factor=0.1),
    ],
    name="img_augmentation",
)
```

This `Sequential` model object can be used both as a part of
the model we later build, and as a function to preprocess
data before feeding into the model. Using them as function makes
it easy to visualize the augmented images. Here we plot 9 examples
of augmentation result of a given figure.


```python
for image, label in ds_train.take(1):
    for i in range(9):
        ax = plt.subplot(3, 3, i + 1)
        aug_img = img_augmentation(tf.expand_dims(image, axis=0))
        plt.imshow(aug_img[0].numpy().astype("uint8"))
        plt.title("{}, {}".format((label), label_info.int2str(label)))
        plt.axis("off")

```


![png](/img/examples/vision/image_classification_efficientnet_fine_tuning/image_classification_efficientnet_fine_tuning_14_0.png)


### Prepare inputs

Once we verify the input data and augmentation are working correctly,
we prepare dataset for training. The input data are resized to uniform
`IMG_SIZE`. The labels are put into one-hot
(a.k.a. categorical) encoding. The dataset is batched.

Note: `cache`, `prefetch` and `AUTOTUNE` may in some situation improve
performance, but depends on environment and the specific dataset used.
See this [guide](https://www.tensorflow.org/guide/data_performance)
for more information on data pipeline performance.


```python
# One-hot / categorical encoding
def input_preprocess(image, label):
    label = tf.one_hot(label, NUM_CLASSES)
    return image, label


ds_train = ds_train.map(
    input_preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE
)
ds_train = ds_train.cache()
ds_train = ds_train.batch(batch_size=batch_size, drop_remainder=True)
ds_train = ds_train.prefetch(tf.data.experimental.AUTOTUNE)

ds_test = ds_test.map(input_preprocess)
ds_test = ds_test.batch(batch_size=batch_size, drop_remainder=True)

```

---
## Training a model from scratch

We build an EfficientNetB0 with 120 output classes, that is initialized from scratch:

Note: the accuracy will increase very slowly and may overfit.


```python
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.optimizers import SGD

with strategy.scope():
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))

    x = img_augmentation(inputs)

    x = EfficientNetB0(include_top=True, weights=None, classes=NUM_CLASSES)(x)

    model = tf.keras.Model(inputs, x)

    sgd = SGD(learning_rate=0.2, momentum=0.1, nesterov=True)
    model.compile(optimizer=sgd, loss="categorical_crossentropy", metrics=["accuracy"])

model.summary()
reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
    monitor="val_loss", factor=0.2, patience=5, min_lr=0.005
)

epochs = 20  # @param {type: "slider", min:5, max:50}
hist = model.fit(
    ds_train, epochs=epochs, validation_data=ds_test, callbacks=[reduce_lr], verbose=2
)

```

<div class="k-default-codeblock">
```
INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

INFO:tensorflow:Reduce to /job:localhost/replica:0/task:0/device:CPU:0 then broadcast to ('/job:localhost/replica:0/task:0/device:CPU:0',).

Model: "functional_1"
_________________________________________________________________
Layer (type)                 Output Shape              Param #   
=================================================================
input_1 (InputLayer)         [(None, 224, 224, 3)]     0         
_________________________________________________________________
img_augmentation (Sequential (None, 224, 224, 3)       0         
_________________________________________________________________
efficientnetb0 (Functional)  (None, 120)               4203291   
=================================================================
Total params: 4,203,291
Trainable params: 4,161,268
Non-trainable params: 42,023
_________________________________________________________________
Epoch 1/20
WARNING:tensorflow:Callbacks method `on_train_batch_end` is slow compared to the batch time (batch time: 0.0919s vs `on_train_batch_end` time: 0.1893s). Check your callbacks.

WARNING:tensorflow:Callbacks method `on_train_batch_end` is slow compared to the batch time (batch time: 0.0919s vs `on_train_batch_end` time: 0.1893s). Check your callbacks.

187/187 - 62s - loss: 4.9634 - accuracy: 0.0128 - val_loss: 4.8171 - val_accuracy: 0.0139
Epoch 2/20
187/187 - 59s - loss: 4.5712 - accuracy: 0.0260 - val_loss: 4.7677 - val_accuracy: 0.0206
Epoch 3/20
187/187 - 60s - loss: 4.3928 - accuracy: 0.0377 - val_loss: 4.4246 - val_accuracy: 0.0351
Epoch 4/20
187/187 - 59s - loss: 4.2694 - accuracy: 0.0460 - val_loss: 4.4778 - val_accuracy: 0.0393
Epoch 5/20
187/187 - 59s - loss: 4.1732 - accuracy: 0.0548 - val_loss: 4.2238 - val_accuracy: 0.0532
Epoch 6/20
187/187 - 59s - loss: 4.0941 - accuracy: 0.0652 - val_loss: 4.0877 - val_accuracy: 0.0648
Epoch 7/20
187/187 - 59s - loss: 4.0204 - accuracy: 0.0705 - val_loss: 4.0757 - val_accuracy: 0.0716
Epoch 8/20
187/187 - 59s - loss: 3.9521 - accuracy: 0.0818 - val_loss: 3.9778 - val_accuracy: 0.0806
Epoch 9/20
187/187 - 59s - loss: 3.8764 - accuracy: 0.0905 - val_loss: 3.9885 - val_accuracy: 0.0914
Epoch 10/20
187/187 - 59s - loss: 3.8021 - accuracy: 0.1029 - val_loss: 3.9583 - val_accuracy: 0.0906
Epoch 11/20
187/187 - 59s - loss: 3.7328 - accuracy: 0.1131 - val_loss: 4.0107 - val_accuracy: 0.0842
Epoch 12/20
187/187 - 59s - loss: 3.6606 - accuracy: 0.1226 - val_loss: 3.9239 - val_accuracy: 0.0997
Epoch 13/20
187/187 - 59s - loss: 3.5945 - accuracy: 0.1359 - val_loss: 4.1540 - val_accuracy: 0.0861
Epoch 14/20
187/187 - 59s - loss: 3.5346 - accuracy: 0.1444 - val_loss: 3.9642 - val_accuracy: 0.1062
Epoch 15/20
187/187 - 58s - loss: 3.4544 - accuracy: 0.1579 - val_loss: 3.7911 - val_accuracy: 0.1236
Epoch 16/20
187/187 - 59s - loss: 3.3867 - accuracy: 0.1680 - val_loss: 3.7947 - val_accuracy: 0.1154
Epoch 17/20
187/187 - 59s - loss: 3.3279 - accuracy: 0.1755 - val_loss: 3.8368 - val_accuracy: 0.1196
Epoch 18/20
187/187 - 59s - loss: 3.2456 - accuracy: 0.1944 - val_loss: 3.6632 - val_accuracy: 0.1409
Epoch 19/20
187/187 - 59s - loss: 3.1877 - accuracy: 0.2048 - val_loss: 3.9556 - val_accuracy: 0.1224
Epoch 20/20
187/187 - 59s - loss: 3.1292 - accuracy: 0.2132 - val_loss: 3.6958 - val_accuracy: 0.1470

```
</div>
Training the model is relatively fast (takes only 20 seconds per epoch on TPUv2 that is
available on colab). This might make it sounds easy to simply train EfficientNet on any
dataset wanted from scratch. However, training EfficientNet on smaller datasets,
especially those with lower resolution like CIFAR-100, faces the significant challenge of
overfitting or getting trapped in local extrema.

Hence traning from scratch requires very careful choice of hyperparameters and is
difficult to find suitable regularization. It would also be much more demanding in resources.
Plotting the training and validation accuracy
makes it clear that validation accuracy stagnates at very low value.


```python
import matplotlib.pyplot as plt


def plot_hist(hist):
    plt.plot(hist.history["accuracy"])
    plt.plot(hist.history["val_accuracy"])
    plt.title("model accuracy")
    plt.ylabel("accuracy")
    plt.xlabel("epoch")
    plt.legend(["train", "validation"], loc="upper left")
    plt.show()


plot_hist(hist)
```


![png](/img/examples/vision/image_classification_efficientnet_fine_tuning/image_classification_efficientnet_fine_tuning_20_0.png)


---
## Transfer learning from pre-trained weights

Here we initialize the model with pre-trained ImageNet weights,
and we fine-tune it on our own dataset.


```python
from tensorflow.keras.layers.experimental import preprocessing


def build_model(num_classes):
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))

    x = img_augmentation(inputs)

    model = EfficientNetB0(include_top=False, input_tensor=x, weights="imagenet")

    # Freeze the pretrained weights
    model.trainable = False

    # Rebuild top
    x = layers.GlobalAveragePooling2D(name="avg_pool")(model.output)
    x = layers.BatchNormalization()(x)

    top_dropout_rate = 0.2
    x = layers.Dropout(top_dropout_rate, name="top_dropout")(x)
    x = layers.Dense(NUM_CLASSES, activation="softmax", name="pred")(x)

    # Compile
    model = tf.keras.Model(inputs, x, name="EfficientNet")
    sgd = SGD(learning_rate=0.2, momentum=0.1, nesterov=True)
    model.compile(optimizer=sgd, loss="categorical_crossentropy", metrics=["accuracy"])
    return model

```

The first step to transfer learning is to freeze all layers and train only the top
layers. For this step, a relatively large learning rate (~0.1) can be used to start with,
while applying some learning rate decay (either `ExponentialDecay` or use the `ReduceLROnPlateau`
callback).  For this stage, using
`EfficientNetB0`, validation accuracy and loss will usually be better than training
accuracy and loss. This is because the regularization is strong, which only
suppresses train time metrics.

Note that the convergence may take up to 50 epochs depending on choice of learning rate.
If image augmentation layers were not
applied, the validation accuracy may only reach ~60%.


```python
from tensorflow.keras.callbacks import ReduceLROnPlateau

with strategy.scope():
    model = build_model(num_classes=NUM_CLASSES)

reduce_lr = ReduceLROnPlateau(monitor="val_loss", factor=0.2, patience=5, min_lr=0.0001)

epochs = 25  # @param {type: "slider", min:8, max:80}
hist = model.fit(
    ds_train, epochs=epochs, validation_data=ds_test, callbacks=[reduce_lr], verbose=2
)
plot_hist(hist)
```

<div class="k-default-codeblock">
```
Epoch 1/25
187/187 - 20s - loss: 2.6554 - accuracy: 0.3859 - val_loss: 0.9579 - val_accuracy: 0.7206
Epoch 2/25
187/187 - 19s - loss: 1.9079 - accuracy: 0.5206 - val_loss: 0.8153 - val_accuracy: 0.7556
Epoch 3/25
187/187 - 18s - loss: 1.6656 - accuracy: 0.5688 - val_loss: 0.8125 - val_accuracy: 0.7696
Epoch 4/25
187/187 - 18s - loss: 1.5515 - accuracy: 0.5900 - val_loss: 0.8203 - val_accuracy: 0.7704
Epoch 5/25
187/187 - 18s - loss: 1.4354 - accuracy: 0.6136 - val_loss: 0.8245 - val_accuracy: 0.7690
Epoch 6/25
187/187 - 18s - loss: 1.3539 - accuracy: 0.6314 - val_loss: 0.8022 - val_accuracy: 0.7725
Epoch 7/25
187/187 - 18s - loss: 1.2835 - accuracy: 0.6451 - val_loss: 0.8010 - val_accuracy: 0.7732
Epoch 8/25
187/187 - 18s - loss: 1.2237 - accuracy: 0.6527 - val_loss: 0.8027 - val_accuracy: 0.7737
Epoch 9/25
187/187 - 18s - loss: 1.2011 - accuracy: 0.6639 - val_loss: 0.8053 - val_accuracy: 0.7674
Epoch 10/25
187/187 - 18s - loss: 1.1383 - accuracy: 0.6788 - val_loss: 0.8098 - val_accuracy: 0.7722
Epoch 11/25
187/187 - 18s - loss: 1.1208 - accuracy: 0.6770 - val_loss: 0.8016 - val_accuracy: 0.7724
Epoch 12/25
187/187 - 18s - loss: 1.0814 - accuracy: 0.6831 - val_loss: 0.7903 - val_accuracy: 0.7766
Epoch 13/25
187/187 - 18s - loss: 1.0567 - accuracy: 0.6919 - val_loss: 0.7604 - val_accuracy: 0.7824
Epoch 14/25
187/187 - 18s - loss: 1.0335 - accuracy: 0.6937 - val_loss: 0.7665 - val_accuracy: 0.7826
Epoch 15/25
187/187 - 18s - loss: 0.9805 - accuracy: 0.7085 - val_loss: 0.7424 - val_accuracy: 0.7879
Epoch 16/25
187/187 - 18s - loss: 0.9999 - accuracy: 0.7060 - val_loss: 0.7794 - val_accuracy: 0.7831
Epoch 17/25
187/187 - 18s - loss: 0.9654 - accuracy: 0.7122 - val_loss: 0.7722 - val_accuracy: 0.7789
Epoch 18/25
187/187 - 18s - loss: 0.9491 - accuracy: 0.7185 - val_loss: 0.7470 - val_accuracy: 0.7875
Epoch 19/25
187/187 - 18s - loss: 0.9724 - accuracy: 0.7184 - val_loss: 0.7660 - val_accuracy: 0.7851
Epoch 20/25
187/187 - 18s - loss: 0.9349 - accuracy: 0.7212 - val_loss: 0.7337 - val_accuracy: 0.7936
Epoch 21/25
187/187 - 18s - loss: 0.9045 - accuracy: 0.7260 - val_loss: 0.7735 - val_accuracy: 0.7829
Epoch 22/25
187/187 - 18s - loss: 0.8963 - accuracy: 0.7247 - val_loss: 0.7823 - val_accuracy: 0.7783
Epoch 23/25
187/187 - 18s - loss: 0.8994 - accuracy: 0.7274 - val_loss: 0.7566 - val_accuracy: 0.7840
Epoch 24/25
187/187 - 18s - loss: 0.8735 - accuracy: 0.7335 - val_loss: 0.7457 - val_accuracy: 0.7912
Epoch 25/25
187/187 - 18s - loss: 0.8691 - accuracy: 0.7345 - val_loss: 0.7428 - val_accuracy: 0.7929

```
</div>
![png](/img/examples/vision/image_classification_efficientnet_fine_tuning/image_classification_efficientnet_fine_tuning_24_1.png)


The second step is to unfreeze a number of layers and fit the model using smaller
learning rate. In this example we show unfreezing all layers, but depending on
specific dataset it may be desireble to only unfreeze a fraction of all layers.

When the feature extraction with
pretrained model works good enough, this step would give a very limited gain on
validation accuracy. The example we show does not see significant improvement
as ImageNet pretraining already exposed the model to a good amount of dogs.

On the other hand, when we use pretrained weights on a dataset that is more different
from ImageNet, this fine-tuning step can be crucial as the feature extractor also
needs to be adjusted by a considerable amount. Such a situation can be demonstrated
if choosing CIFAR-100 dataset instead, where fine-tuning boosts validation accuracy
by about 10% to pass 80% on `EfficientNetB0`.
In such a case the convergence may take more than 50 epochs.

A side note on freezing/unfreezing models: setting `trainable` of a `Model` will
simultaneously set all layers belonging to the `Model` to the same `trainable`
attribute. Each layer is trainable only if both the layer itself and the model
containing it are trainable. Hence when we need to partially freeze/unfreeze
a model, we need to make sure the `trainable` attribute of the model is set
to `True`.


```python

def unfreeze_model(model):
    model.trainable = True
    for l in model.layers:
        if isinstance(l, layers.BatchNormalization):
            print(f"{l.name} is staying untrainable")
            l.trainable = False

    sgd = SGD(learning_rate=0.0004)
    model.compile(optimizer=sgd, loss="categorical_crossentropy", metrics=["accuracy"])


unfreeze_model(model)

reduce_lr = ReduceLROnPlateau(
    monitor="val_loss", factor=0.2, patience=5, min_lr=0.00001
)
epochs = 25  # @param {type: "slider", min:8, max:80}
hist = model.fit(
    ds_train, epochs=epochs, validation_data=ds_test, callbacks=[reduce_lr], verbose=2
)
plot_hist(hist)
```

<div class="k-default-codeblock">
```
stem_bn is staying untrainable
block1a_bn is staying untrainable
block1a_project_bn is staying untrainable
block2a_expand_bn is staying untrainable
block2a_bn is staying untrainable
block2a_project_bn is staying untrainable
block2b_expand_bn is staying untrainable
block2b_bn is staying untrainable
block2b_project_bn is staying untrainable
block3a_expand_bn is staying untrainable
block3a_bn is staying untrainable
block3a_project_bn is staying untrainable
block3b_expand_bn is staying untrainable
block3b_bn is staying untrainable
block3b_project_bn is staying untrainable
block4a_expand_bn is staying untrainable
block4a_bn is staying untrainable
block4a_project_bn is staying untrainable
block4b_expand_bn is staying untrainable
block4b_bn is staying untrainable
block4b_project_bn is staying untrainable
block4c_expand_bn is staying untrainable
block4c_bn is staying untrainable
block4c_project_bn is staying untrainable
block5a_expand_bn is staying untrainable
block5a_bn is staying untrainable
block5a_project_bn is staying untrainable
block5b_expand_bn is staying untrainable
block5b_bn is staying untrainable
block5b_project_bn is staying untrainable
block5c_expand_bn is staying untrainable
block5c_bn is staying untrainable
block5c_project_bn is staying untrainable
block6a_expand_bn is staying untrainable
block6a_bn is staying untrainable
block6a_project_bn is staying untrainable
block6b_expand_bn is staying untrainable
block6b_bn is staying untrainable
block6b_project_bn is staying untrainable
block6c_expand_bn is staying untrainable
block6c_bn is staying untrainable
block6c_project_bn is staying untrainable
block6d_expand_bn is staying untrainable
block6d_bn is staying untrainable
block6d_project_bn is staying untrainable
block7a_expand_bn is staying untrainable
block7a_bn is staying untrainable
block7a_project_bn is staying untrainable
top_bn is staying untrainable
batch_normalization is staying untrainable
Epoch 1/25
WARNING:tensorflow:Callbacks method `on_train_batch_end` is slow compared to the batch time (batch time: 0.0933s vs `on_train_batch_end` time: 0.1810s). Check your callbacks.

WARNING:tensorflow:Callbacks method `on_train_batch_end` is slow compared to the batch time (batch time: 0.0933s vs `on_train_batch_end` time: 0.1810s). Check your callbacks.

187/187 - 64s - loss: 0.7429 - accuracy: 0.7724 - val_loss: 0.7360 - val_accuracy: 0.7970
Epoch 2/25
187/187 - 61s - loss: 0.6910 - accuracy: 0.7815 - val_loss: 0.7471 - val_accuracy: 0.7947
Epoch 3/25
187/187 - 61s - loss: 0.6713 - accuracy: 0.7908 - val_loss: 0.7570 - val_accuracy: 0.7948
Epoch 4/25
187/187 - 62s - loss: 0.6540 - accuracy: 0.7955 - val_loss: 0.7491 - val_accuracy: 0.7947
Epoch 5/25
187/187 - 61s - loss: 0.6439 - accuracy: 0.7979 - val_loss: 0.7550 - val_accuracy: 0.7937
Epoch 6/25
187/187 - 62s - loss: 0.6248 - accuracy: 0.8034 - val_loss: 0.7805 - val_accuracy: 0.7894
Epoch 7/25
187/187 - 61s - loss: 0.6072 - accuracy: 0.8102 - val_loss: 0.7701 - val_accuracy: 0.7905
Epoch 8/25
187/187 - 62s - loss: 0.6150 - accuracy: 0.8061 - val_loss: 0.7752 - val_accuracy: 0.7889
Epoch 9/25
187/187 - 61s - loss: 0.6000 - accuracy: 0.8092 - val_loss: 0.7706 - val_accuracy: 0.7899
Epoch 10/25
187/187 - 59s - loss: 0.5896 - accuracy: 0.8122 - val_loss: 0.7658 - val_accuracy: 0.7902
Epoch 11/25
187/187 - 61s - loss: 0.6067 - accuracy: 0.8102 - val_loss: 0.7726 - val_accuracy: 0.7898
Epoch 12/25
187/187 - 61s - loss: 0.5889 - accuracy: 0.8171 - val_loss: 0.7687 - val_accuracy: 0.7905
Epoch 13/25
187/187 - 61s - loss: 0.5807 - accuracy: 0.8168 - val_loss: 0.7693 - val_accuracy: 0.7903
Epoch 14/25
187/187 - 61s - loss: 0.5644 - accuracy: 0.8204 - val_loss: 0.7687 - val_accuracy: 0.7905
Epoch 15/25
187/187 - 62s - loss: 0.5875 - accuracy: 0.8163 - val_loss: 0.7667 - val_accuracy: 0.7908
Epoch 16/25
187/187 - 61s - loss: 0.5977 - accuracy: 0.8051 - val_loss: 0.7685 - val_accuracy: 0.7909
Epoch 17/25
187/187 - 61s - loss: 0.5978 - accuracy: 0.8141 - val_loss: 0.7671 - val_accuracy: 0.7909
Epoch 18/25
187/187 - 61s - loss: 0.5835 - accuracy: 0.8154 - val_loss: 0.7667 - val_accuracy: 0.7909
Epoch 19/25
187/187 - 62s - loss: 0.5998 - accuracy: 0.8112 - val_loss: 0.7666 - val_accuracy: 0.7908
Epoch 20/25
187/187 - 61s - loss: 0.5990 - accuracy: 0.8123 - val_loss: 0.7679 - val_accuracy: 0.7910
Epoch 21/25
187/187 - 61s - loss: 0.5860 - accuracy: 0.8168 - val_loss: 0.7698 - val_accuracy: 0.7901
Epoch 22/25
187/187 - 61s - loss: 0.5989 - accuracy: 0.8080 - val_loss: 0.7694 - val_accuracy: 0.7910
Epoch 23/25
187/187 - 61s - loss: 0.5778 - accuracy: 0.8171 - val_loss: 0.7686 - val_accuracy: 0.7909
Epoch 24/25
187/187 - 60s - loss: 0.5885 - accuracy: 0.8174 - val_loss: 0.7685 - val_accuracy: 0.7915
Epoch 25/25
187/187 - 61s - loss: 0.5785 - accuracy: 0.8158 - val_loss: 0.7688 - val_accuracy: 0.7907

```
</div>
![png](/img/examples/vision/image_classification_efficientnet_fine_tuning/image_classification_efficientnet_fine_tuning_26_3.png)


### Tips for fine tuning EfficientNet

On unfreezing layers:

- The `BathcNormalization` layers need to be kept frozen
([more details](https://keras.io/guides/transfer_learning/)).
If they are also turned to trainable, the
first epoch after unfreezing will significantly reduce accuracy.
- In some cases it may be beneficial to open up only a portion of layers instead of
unfreezing all. This will make fine tuning much faster when going to larger models like
B7.
- Each block needs to be all turned on or off. This is because the architecture includes
a shortcut from the first layer to the last layer for each block. Not respecting blocks
also significantly harms the final performance.

Some other tips for utilizing EfficientNet:

- Larger variants of EfficientNet do not guarantee improved performance, especially for
tasks with less data or fewer classes. In such a case, the larger variant of EfficientNet
chosen, the harder it is to tune hyperparameters.
- EMA (Exponential Moving Average) is very helpful in training EfficientNet from scratch,
but not so much for transfer learning.
- Do not use the RMSprop setup as in the original paper for transfer learning. The
momentum and learning rate are too high for transfer learning. It will easily corrupt the
pretrained weight and blow up the loss. A quick check is to see if loss (as categorical
cross entropy) is getting significantly larger than log(NUM_CLASSES) after the same
epoch. If so, the initial learning rate/momentum is too high.
- Smaller batch size benefit validation accuracy, possibly due to effectively providing
regularization.

---
## Using the latest EfficientNet weights

Since the initial paper, the EfficientNet has been improved by various methods for data
preprocessing and for using unlabelled data to enhance learning results. These
improvements are relatively hard and computationally costly to reproduce, and require
extra code; but the weights are readily available in the form of TF checkpoint files. The
model architecture has not changed, so loading the improved checkpoints is possible.

To use a checkpoint provided at
[the official model repository](https://github.com/tensorflow/tpu/tree/master/models/official/efficientnet), first
download the checkpoint. As example, here we download noisy-student version of B1:

```
!wget https://storage.googleapis.com/cloud-tpu-checkpoints/efficientnet\
       /noisystudent/noisy_student_efficientnet-b1.tar.gz
!tar -xf noisy_student_efficientnet-b1.tar.gz
```

Then use the script efficientnet_weight_update_util.py to convert ckpt file to h5 file.

```
!python efficientnet_weight_update_util.py --model b1 --notop --ckpt \
        efficientnet-b1/model.ckpt --o efficientnetb1_notop.h5
```

When creating model, use the following to load new weight:

```python
model = EfficientNetB0(weights="efficientnetb1_notop.h5", include_top=False)
```
