# Video Vision Transformer

**Author:** [Aritra Roy Gosthipaty](https://twitter.com/ariG23498), [Ayush Thakur](https://twitter.com/ayushthakur0) (equal contribution)<br>
**Date created:** 2022/01/12<br>
**Last modified:**  2024/01/13<br>
**Description:** A Transformer-based architecture for video classification.


<img class="k-inline-icon" src="https://colab.research.google.com/img/colab_favicon.ico"/> [**View in Colab**](https://colab.research.google.com/github/keras-team/keras-io/blob/master/examples/vision/ipynb/vivit.ipynb)  <span class="k-dot">•</span><img class="k-inline-icon" src="https://github.com/favicon.ico"/> [**GitHub source**](https://github.com/keras-team/keras-io/blob/master/examples/vision/vivit.py)



---
## Introduction

Videos are sequences of images. Let's assume you have an image
representation model (CNN, ViT, etc.) and a sequence model
(RNN, LSTM, etc.) at hand. We ask you to tweak the model for video
classification. The simplest approach would be to apply the image
model to individual frames, use the sequence model to learn
sequences of image features, then apply a classification head on
the learned sequence representation.
The Keras example
[Video Classification with a CNN-RNN Architecture](https://keras.io/examples/vision/video_classification/)
explains this approach in detail. Alernatively, you can also
build a hybrid Transformer-based model for video classification as shown in the Keras example
[Video Classification with Transformers](https://keras.io/examples/vision/video_transformers/).

In this example, we minimally implement
[ViViT: A Video Vision Transformer](https://arxiv.org/abs/2103.15691)
by Arnab et al., a **pure Transformer-based** model
for video classification. The authors propose a novel embedding scheme
and a number of Transformer variants to model video clips. We implement
the embedding scheme and one of the variants of the Transformer
architecture, for simplicity.

This example requires the `medmnist`
package, which can be installed by running the code cell below.


```python
!pip install -qq medmnist
```

---
## Imports


```python
import os
import io
import imageio
import medmnist
import ipywidgets
import numpy as np

import keras
import tensorflow as tf
from keras import layers
from keras import ops

# Setting seed for reproducibility
SEED = 42
os.environ["TF_CUDNN_DETERMINISTIC"] = "1"
keras.utils.set_random_seed(SEED)
```

---
## Hyperparameters

The hyperparameters are chosen via hyperparameter
search. You can learn more about the process in the "conclusion" section.


```python
# DATA
DATASET_NAME = "organmnist3d"
BATCH_SIZE = 32
AUTO = tf.data.AUTOTUNE
INPUT_SHAPE = (28, 28, 28, 1)
NUM_CLASSES = 11

# OPTIMIZER
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-5

# TRAINING
EPOCHS = 60

# TUBELET EMBEDDING
PATCH_SIZE = (8, 8, 8)
NUM_PATCHES = (INPUT_SHAPE[0] // PATCH_SIZE[0]) ** 2

# ViViT ARCHITECTURE
LAYER_NORM_EPS = 1e-6
PROJECTION_DIM = 128
NUM_HEADS = 8
NUM_LAYERS = 8
```

---
## Dataset

For our example we use the
[MedMNIST v2: A Large-Scale Lightweight Benchmark for 2D and 3D Biomedical Image Classification](https://medmnist.com/)
dataset. The videos are lightweight and easy to train on.


```python

def download_and_prepare_dataset(data_info: dict):
    """Utility function to download the dataset.

    Arguments:
        data_info (dict): Dataset metadata.
    """
    data_path = keras.utils.get_file(origin=data_info["url"], md5_hash=data_info["MD5"])

    with np.load(data_path) as data:
        # Get videos
        train_videos = data["train_images"]
        valid_videos = data["val_images"]
        test_videos = data["test_images"]

        # Get labels
        train_labels = data["train_labels"].flatten()
        valid_labels = data["val_labels"].flatten()
        test_labels = data["test_labels"].flatten()

    return (
        (train_videos, train_labels),
        (valid_videos, valid_labels),
        (test_videos, test_labels),
    )


# Get the metadata of the dataset
info = medmnist.INFO[DATASET_NAME]

# Get the dataset
prepared_dataset = download_and_prepare_dataset(info)
(train_videos, train_labels) = prepared_dataset[0]
(valid_videos, valid_labels) = prepared_dataset[1]
(test_videos, test_labels) = prepared_dataset[2]
```

<div class="k-default-codeblock">
```
Downloading data from https://zenodo.org/record/6496656/files/organmnist3d.npz?download=1

```
</div>
    
        0/32657407 [37m━━━━━━━━━━━━━━━━━━━━  0s 0s/step

<div class="k-default-codeblock">
```

```
</div>
    16384/32657407 [37m━━━━━━━━━━━━━━━━━━━━  4:24 8us/step

<div class="k-default-codeblock">
```

```
</div>
    49152/32657407 [37m━━━━━━━━━━━━━━━━━━━━  2:57 5us/step

<div class="k-default-codeblock">
```

```
</div>
   122880/32657407 [37m━━━━━━━━━━━━━━━━━━━━  1:47 3us/step

<div class="k-default-codeblock">
```

```
</div>
   147456/32657407 [37m━━━━━━━━━━━━━━━━━━━━  1:42 3us/step

<div class="k-default-codeblock">
```

```
</div>
   245760/32657407 [37m━━━━━━━━━━━━━━━━━━━━  1:14 2us/step

<div class="k-default-codeblock">
```

```
</div>
   303104/32657407 [37m━━━━━━━━━━━━━━━━━━━━  1:10 2us/step

<div class="k-default-codeblock">
```

```
</div>
   507904/32657407 [37m━━━━━━━━━━━━━━━━━━━━  46s 1us/step 

<div class="k-default-codeblock">
```

```
</div>
   557056/32657407 [37m━━━━━━━━━━━━━━━━━━━━  48s 2us/step

<div class="k-default-codeblock">
```

```
</div>
   770048/32657407 [37m━━━━━━━━━━━━━━━━━━━━  37s 1us/step

<div class="k-default-codeblock">
```

```
</div>
   868352/32657407 [37m━━━━━━━━━━━━━━━━━━━━  37s 1us/step

<div class="k-default-codeblock">
```

```
</div>
   917504/32657407 [37m━━━━━━━━━━━━━━━━━━━━  37s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1081344/32657407 [37m━━━━━━━━━━━━━━━━━━━━  32s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1212416/32657407 [37m━━━━━━━━━━━━━━━━━━━━  31s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1277952/32657407 [37m━━━━━━━━━━━━━━━━━━━━  31s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1392640/32657407 [37m━━━━━━━━━━━━━━━━━━━━  30s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1605632/32657407 [37m━━━━━━━━━━━━━━━━━━━━  27s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1638400/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  29s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1769472/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  27s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  1998848/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  26s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2129920/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  25s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2277376/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  24s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2359296/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  24s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2449408/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  24s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2646016/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  23s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2801664/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  22s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  2940928/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  21s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3055616/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  21s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3104768/32657407 ━[37m━━━━━━━━━━━━━━━━━━━  21s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3276800/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3399680/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3514368/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3661824/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3710976/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  3842048/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  21s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4055040/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4333568/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4481024/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4513792/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4612096/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4661248/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  20s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  4857856/32657407 ━━[37m━━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5021696/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5087232/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5251072/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5300224/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  19s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5447680/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5562368/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5595136/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5758976/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5840896/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5857280/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  5922816/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6119424/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6152192/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6217728/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6430720/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6463488/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6529024/32657407 ━━━[37m━━━━━━━━━━━━━━━━━  18s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6651904/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6750208/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6799360/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  6930432/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7045120/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7094272/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7184384/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7389184/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7421952/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7602176/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7700480/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7798784/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  17s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  7979008/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8044544/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8142848/32657407 ━━━━[37m━━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8290304/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8339456/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8437760/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8568832/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8634368/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8716288/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8896512/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  8962048/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9011200/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  16s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9109504/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9224192/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9306112/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9355264/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9502720/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9601024/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9650176/32657407 ━━━━━[37m━━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9814016/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9936896/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
  9945088/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10092544/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  15s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10190848/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10240000/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10338304/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10485760/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10551296/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10633216/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10756096/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10870784/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 10887168/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11001856/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11083776/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11182080/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11231232/32657407 ━━━━━━[37m━━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11460608/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11476992/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11526144/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11575296/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11788288/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11821056/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 11886592/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  14s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12115968/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12165120/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12214272/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12443648/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12476416/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12509184/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12673024/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12804096/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 12984320/32657407 ━━━━━━━[37m━━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13099008/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13131776/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  13s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13312000/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13410304/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13426688/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13475840/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13557760/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13688832/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13737984/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 13869056/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14049280/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14131200/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14327808/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14344192/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14409728/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14458880/32657407 ━━━━━━━━[37m━━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14704640/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14770176/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 14893056/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15024128/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  12s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15089664/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15187968/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15335424/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15384576/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15597568/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15663104/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15712256/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 15810560/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16007168/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16072704/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16318464/32657407 ━━━━━━━━━[37m━━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16367616/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  11s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16629760/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16678912/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 16777216/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17006592/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17063936/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17268736/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17350656/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17440768/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17481728/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17694720/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  10s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 17776640/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  9s 1us/step 

<div class="k-default-codeblock">
```

```
</div>
 17891328/32657407 ━━━━━━━━━━[37m━━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18071552/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18202624/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18317312/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18481152/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18612224/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18710528/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18825216/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 18939904/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  9s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19038208/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19161088/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19243008/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19374080/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19537920/32657407 ━━━━━━━━━━━[37m━━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19619840/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19734528/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 19931136/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20094976/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20242432/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  8s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20439040/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20504576/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20652032/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20799488/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 20914176/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21028864/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21159936/32657407 ━━━━━━━━━━━━[37m━━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21323776/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21422080/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21536768/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21684224/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  7s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21848064/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21897216/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 21995520/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 22126592/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 22298624/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 22421504/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 22552576/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 22650880/32657407 ━━━━━━━━━━━━━[37m━━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 22863872/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23027712/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23093248/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  6s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23224320/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23322624/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23511040/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23625728/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23691264/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23904256/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 23986176/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24133632/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24199168/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24281088/32657407 ━━━━━━━━━━━━━━[37m━━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24510464/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  5s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24739840/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24772608/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 24936448/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 25001984/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 25296896/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 25444352/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 25526272/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 25624576/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 25772032/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 26083328/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 26116096/32657407 ━━━━━━━━━━━━━━━[37m━━━━━  4s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 26230784/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 26345472/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 26558464/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 26722304/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 27033600/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 27377664/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 27541504/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 27615232/32657407 ━━━━━━━━━━━━━━━━[37m━━━━  3s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 27844608/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 27975680/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28155904/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28246016/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28434432/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28532736/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28680192/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28860416/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 28991488/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29040640/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29155328/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29270016/32657407 ━━━━━━━━━━━━━━━━━[37m━━━  2s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29450240/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29630464/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29761536/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 29958144/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30089216/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30269440/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30367744/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30564352/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30744576/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30875648/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  1s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 30990336/32657407 ━━━━━━━━━━━━━━━━━━[37m━━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31064064/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31252480/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31481856/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31596544/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31662080/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31801344/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 31932416/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 32079872/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 32194560/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 32309248/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 32440320/32657407 ━━━━━━━━━━━━━━━━━━━[37m━  0s 1us/step

<div class="k-default-codeblock">
```

```
</div>
 32657407/32657407 ━━━━━━━━━━━━━━━━━━━━ 19s 1us/step


### `tf.data` pipeline


```python

def preprocess(frames, label):
    """Preprocess the frames tensors and parse the labels."""
    # Preprocess images
    frames = ops.cast(frames, "float32")
    frames = ops.expand_dims(
        frames, axis=-1
    )  # The new axis is to help for further processing with Conv3D layers
    # Parse label
    label = ops.cast(label, "float32")
    return frames, label


def prepare_dataloader(
    videos: np.ndarray,
    labels: np.ndarray,
    loader_type: str = "train",
    batch_size: int = BATCH_SIZE,
):
    """Utility function to prepare the dataloader."""
    dataset = tf.data.Dataset.from_tensor_slices((videos, labels))

    if loader_type == "train":
        dataset = dataset.shuffle(BATCH_SIZE * 2)

    dataloader = (
        dataset.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )
    return dataloader


trainloader = prepare_dataloader(train_videos, train_labels, "train")
validloader = prepare_dataloader(valid_videos, valid_labels, "valid")
testloader = prepare_dataloader(test_videos, test_labels, "test")
```

---
## Tubelet Embedding

In ViTs, an image is divided into patches, which are then spatially
flattened, a process known as tokenization. For a video, one can
repeat this process for individual frames. **Uniform frame sampling**
as suggested by the authors is a tokenization scheme in which we
sample frames from the video clip and perform simple ViT tokenization.

| ![uniform frame sampling](https://i.imgur.com/aaPyLPX.png) |
| :--: |
| Uniform Frame Sampling [Source](https://arxiv.org/abs/2103.15691) |

**Tubelet Embedding** is different in terms of capturing temporal
information from the video.
First, we extract volumes from the video -- these volumes contain
patches of the frame and the temporal information as well. The volumes
are then flattened to build video tokens.

| ![tubelet embedding](https://i.imgur.com/9G7QTfV.png) |
| :--: |
| Tubelet Embedding [Source](https://arxiv.org/abs/2103.15691) |


```python

class TubeletEmbedding(layers.Layer):
    def __init__(self, embed_dim, patch_size, **kwargs):
        super().__init__(**kwargs)
        self.projection = layers.Conv3D(
            filters=embed_dim,
            kernel_size=patch_size,
            strides=patch_size,
            padding="VALID",
        )
        self.flatten = layers.Reshape(target_shape=(-1, embed_dim))

    def call(self, videos):
        projected_patches = self.projection(videos)
        flattened_patches = self.flatten(projected_patches)
        return flattened_patches

```

---
## Positional Embedding

This layer adds positional information to the encoded video tokens.


```python

class PositionalEncoder(layers.Layer):
    def __init__(self, embed_dim, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim

    def build(self, input_shape):
        _, num_tokens, _ = input_shape
        self.position_embedding = layers.Embedding(
            input_dim=num_tokens, output_dim=self.embed_dim
        )
        self.positions = ops.arange(start=0, stop=num_tokens, step=1)

    def call(self, encoded_tokens):
        # Encode the positions and add it to the encoded tokens
        encoded_positions = self.position_embedding(self.positions)
        encoded_tokens = encoded_tokens + encoded_positions
        return encoded_tokens

```

---
## Video Vision Transformer

The authors suggest 4 variants of Vision Transformer:

- Spatio-temporal attention
- Factorized encoder
- Factorized self-attention
- Factorized dot-product attention

In this example, we will implement the **Spatio-temporal attention**
model for simplicity. The following code snippet is heavily inspired from
[Image classification with Vision Transformer](https://keras.io/examples/vision/image_classification_with_vision_transformer/).
One can also refer to the
[official repository of ViViT](https://github.com/google-research/scenic/tree/main/scenic/projects/vivit)
which contains all the variants, implemented in JAX.


```python

def create_vivit_classifier(
    tubelet_embedder,
    positional_encoder,
    input_shape=INPUT_SHAPE,
    transformer_layers=NUM_LAYERS,
    num_heads=NUM_HEADS,
    embed_dim=PROJECTION_DIM,
    layer_norm_eps=LAYER_NORM_EPS,
    num_classes=NUM_CLASSES,
):
    # Get the input layer
    inputs = layers.Input(shape=input_shape)
    # Create patches.
    patches = tubelet_embedder(inputs)
    # Encode patches.
    encoded_patches = positional_encoder(patches)

    # Create multiple layers of the Transformer block.
    for _ in range(transformer_layers):
        # Layer normalization and MHSA
        x1 = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=embed_dim // num_heads, dropout=0.1
        )(x1, x1)

        # Skip connection
        x2 = layers.Add()([attention_output, encoded_patches])

        # Layer Normalization and MLP
        x3 = layers.LayerNormalization(epsilon=1e-6)(x2)
        x3 = keras.Sequential(
            [
                layers.Dense(units=embed_dim * 4, activation="gelu"),
                layers.Dense(units=embed_dim, activation="gelu"),
            ]
        )(x3)

        # Skip connection
        encoded_patches = layers.Add()([x3, x2])

    # Layer normalization and Global average pooling.
    representation = layers.LayerNormalization(epsilon=layer_norm_eps)(encoded_patches)
    representation = layers.GlobalAvgPool1D()(representation)

    # Classify outputs.
    outputs = layers.Dense(units=num_classes, activation="softmax")(representation)

    # Create the Keras model.
    model = keras.Model(inputs=inputs, outputs=outputs)
    return model

```

---
## Train


```python

def run_experiment():
    # Initialize model
    model = create_vivit_classifier(
        tubelet_embedder=TubeletEmbedding(
            embed_dim=PROJECTION_DIM, patch_size=PATCH_SIZE
        ),
        positional_encoder=PositionalEncoder(embed_dim=PROJECTION_DIM),
    )

    # Compile the model with the optimizer, loss function
    # and the metrics.
    optimizer = keras.optimizers.Adam(learning_rate=LEARNING_RATE)
    model.compile(
        optimizer=optimizer,
        loss="sparse_categorical_crossentropy",
        metrics=[
            keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            keras.metrics.SparseTopKCategoricalAccuracy(5, name="top-5-accuracy"),
        ],
    )

    # Train the model.
    _ = model.fit(trainloader, epochs=EPOCHS, validation_data=validloader)

    _, accuracy, top_5_accuracy = model.evaluate(testloader)
    print(f"Test accuracy: {round(accuracy * 100, 2)}%")
    print(f"Test top 5 accuracy: {round(top_5_accuracy * 100, 2)}%")

    return model


model = run_experiment()
```

<div class="k-default-codeblock">
```
Epoch 1/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  11:25 23s/step - accuracy: 0.1250 - loss: 2.5340 - top-5-accuracy: 0.5938

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  1:08 2s/step - accuracy: 0.1328 - loss: 2.6747 - top-5-accuracy: 0.5859  

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  1:08 2s/step - accuracy: 0.1233 - loss: 2.7983 - top-5-accuracy: 0.5816

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  53s 2s/step - accuracy: 0.1257 - loss: 2.8411 - top-5-accuracy: 0.5729 

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  44s 2s/step - accuracy: 0.1218 - loss: 2.8605 - top-5-accuracy: 0.5683

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  39s 2s/step - accuracy: 0.1206 - loss: 2.8665 - top-5-accuracy: 0.5648

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  33s 1s/step - accuracy: 0.1199 - loss: 2.8636 - top-5-accuracy: 0.5638

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  29s 1s/step - accuracy: 0.1191 - loss: 2.8626 - top-5-accuracy: 0.5612

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  25s 1s/step - accuracy: 0.1182 - loss: 2.8614 - top-5-accuracy: 0.5579

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  23s 1s/step - accuracy: 0.1189 - loss: 2.8562 - top-5-accuracy: 0.5558

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  21s 1s/step - accuracy: 0.1197 - loss: 2.8503 - top-5-accuracy: 0.5544

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  19s 1s/step - accuracy: 0.1212 - loss: 2.8426 - top-5-accuracy: 0.5524

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  18s 1s/step - accuracy: 0.1223 - loss: 2.8341 - top-5-accuracy: 0.5514

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  17s 1s/step - accuracy: 0.1231 - loss: 2.8254 - top-5-accuracy: 0.5499

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  15s 988ms/step - accuracy: 0.1236 - loss: 2.8168 - top-5-accuracy: 0.5483

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  15s 1s/step - accuracy: 0.1240 - loss: 2.8078 - top-5-accuracy: 0.5477   

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  13s 965ms/step - accuracy: 0.1241 - loss: 2.7988 - top-5-accuracy: 0.5477

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  12s 931ms/step - accuracy: 0.1240 - loss: 2.7909 - top-5-accuracy: 0.5474

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  10s 900ms/step - accuracy: 0.1237 - loss: 2.7832 - top-5-accuracy: 0.5473

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  9s 894ms/step - accuracy: 0.1235 - loss: 2.7754 - top-5-accuracy: 0.5475 

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  8s 888ms/step - accuracy: 0.1230 - loss: 2.7686 - top-5-accuracy: 0.5475

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  7s 875ms/step - accuracy: 0.1227 - loss: 2.7622 - top-5-accuracy: 0.5474

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  6s 863ms/step - accuracy: 0.1225 - loss: 2.7553 - top-5-accuracy: 0.5476

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  6s 877ms/step - accuracy: 0.1223 - loss: 2.7487 - top-5-accuracy: 0.5478

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  5s 865ms/step - accuracy: 0.1222 - loss: 2.7424 - top-5-accuracy: 0.5479

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  4s 862ms/step - accuracy: 0.1220 - loss: 2.7362 - top-5-accuracy: 0.5483

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  3s 852ms/step - accuracy: 0.1218 - loss: 2.7302 - top-5-accuracy: 0.5487

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  2s 836ms/step - accuracy: 0.1216 - loss: 2.7244 - top-5-accuracy: 0.5489

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 819ms/step - accuracy: 0.1215 - loss: 2.7188 - top-5-accuracy: 0.5491

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 803ms/step - accuracy: 0.1213 - loss: 2.7133 - top-5-accuracy: 0.5494

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 782ms/step - accuracy: 0.1212 - loss: 2.7080 - top-5-accuracy: 0.5497

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 49s 859ms/step - accuracy: 0.1210 - loss: 2.7030 - top-5-accuracy: 0.5499 - val_accuracy: 0.1056 - val_loss: 2.4477 - val_top-5-accuracy: 0.5342


<div class="k-default-codeblock">
```
Epoch 2/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  28s 955ms/step - accuracy: 0.1250 - loss: 2.2942 - top-5-accuracy: 0.6562

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 480ms/step - accuracy: 0.1484 - loss: 2.2799 - top-5-accuracy: 0.6484

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 498ms/step - accuracy: 0.1510 - loss: 2.2750 - top-5-accuracy: 0.6476

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  13s 506ms/step - accuracy: 0.1543 - loss: 2.2742 - top-5-accuracy: 0.6419

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 507ms/step - accuracy: 0.1534 - loss: 2.2805 - top-5-accuracy: 0.6348

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  12s 507ms/step - accuracy: 0.1522 - loss: 2.2853 - top-5-accuracy: 0.6288

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  11s 488ms/step - accuracy: 0.1515 - loss: 2.2893 - top-5-accuracy: 0.6232

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 472ms/step - accuracy: 0.1511 - loss: 2.2918 - top-5-accuracy: 0.6185

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 459ms/step - accuracy: 0.1513 - loss: 2.2926 - top-5-accuracy: 0.6146

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  9s 461ms/step - accuracy: 0.1521 - loss: 2.2927 - top-5-accuracy: 0.6116 

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  9s 463ms/step - accuracy: 0.1525 - loss: 2.2931 - top-5-accuracy: 0.6092

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 465ms/step - accuracy: 0.1532 - loss: 2.2936 - top-5-accuracy: 0.6073

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  8s 467ms/step - accuracy: 0.1536 - loss: 2.2933 - top-5-accuracy: 0.6062

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 468ms/step - accuracy: 0.1540 - loss: 2.2927 - top-5-accuracy: 0.6056

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 469ms/step - accuracy: 0.1543 - loss: 2.2919 - top-5-accuracy: 0.6054

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 470ms/step - accuracy: 0.1546 - loss: 2.2913 - top-5-accuracy: 0.6049

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 470ms/step - accuracy: 0.1551 - loss: 2.2907 - top-5-accuracy: 0.6044

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  6s 470ms/step - accuracy: 0.1553 - loss: 2.2904 - top-5-accuracy: 0.6036

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 471ms/step - accuracy: 0.1558 - loss: 2.2901 - top-5-accuracy: 0.6029

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 466ms/step - accuracy: 0.1561 - loss: 2.2896 - top-5-accuracy: 0.6024

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 462ms/step - accuracy: 0.1561 - loss: 2.2891 - top-5-accuracy: 0.6022

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 471ms/step - accuracy: 0.1562 - loss: 2.2885 - top-5-accuracy: 0.6020

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 477ms/step - accuracy: 0.1562 - loss: 2.2880 - top-5-accuracy: 0.6020

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 481ms/step - accuracy: 0.1562 - loss: 2.2875 - top-5-accuracy: 0.6022

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 485ms/step - accuracy: 0.1561 - loss: 2.2869 - top-5-accuracy: 0.6024

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 489ms/step - accuracy: 0.1558 - loss: 2.2864 - top-5-accuracy: 0.6026

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 485ms/step - accuracy: 0.1556 - loss: 2.2861 - top-5-accuracy: 0.6027

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 481ms/step - accuracy: 0.1553 - loss: 2.2858 - top-5-accuracy: 0.6028

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 487ms/step - accuracy: 0.1550 - loss: 2.2854 - top-5-accuracy: 0.6031

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 491ms/step - accuracy: 0.1548 - loss: 2.2850 - top-5-accuracy: 0.6034

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 480ms/step - accuracy: 0.1546 - loss: 2.2845 - top-5-accuracy: 0.6037

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 16s 502ms/step - accuracy: 0.1544 - loss: 2.2841 - top-5-accuracy: 0.6040 - val_accuracy: 0.1801 - val_loss: 2.3553 - val_top-5-accuracy: 0.4783


<div class="k-default-codeblock">
```
Epoch 3/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  11s 374ms/step - accuracy: 0.1250 - loss: 2.2688 - top-5-accuracy: 0.5625

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 370ms/step - accuracy: 0.1641 - loss: 2.2296 - top-5-accuracy: 0.6016

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 366ms/step - accuracy: 0.1719 - loss: 2.2362 - top-5-accuracy: 0.5920

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  10s 393ms/step - accuracy: 0.1738 - loss: 2.2406 - top-5-accuracy: 0.5885

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 397ms/step - accuracy: 0.1753 - loss: 2.2420 - top-5-accuracy: 0.5896

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 407ms/step - accuracy: 0.1739 - loss: 2.2444 - top-5-accuracy: 0.5903

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  10s 451ms/step - accuracy: 0.1714 - loss: 2.2453 - top-5-accuracy: 0.5946

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 488ms/step - accuracy: 0.1690 - loss: 2.2446 - top-5-accuracy: 0.5979

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 477ms/step - accuracy: 0.1668 - loss: 2.2442 - top-5-accuracy: 0.6005

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  9s 468ms/step - accuracy: 0.1654 - loss: 2.2440 - top-5-accuracy: 0.6020 

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  9s 458ms/step - accuracy: 0.1646 - loss: 2.2437 - top-5-accuracy: 0.6036

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 450ms/step - accuracy: 0.1654 - loss: 2.2420 - top-5-accuracy: 0.6069

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 444ms/step - accuracy: 0.1660 - loss: 2.2403 - top-5-accuracy: 0.6103

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 439ms/step - accuracy: 0.1666 - loss: 2.2387 - top-5-accuracy: 0.6135

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 435ms/step - accuracy: 0.1671 - loss: 2.2373 - top-5-accuracy: 0.6163

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 433ms/step - accuracy: 0.1676 - loss: 2.2362 - top-5-accuracy: 0.6183

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 433ms/step - accuracy: 0.1677 - loss: 2.2351 - top-5-accuracy: 0.6202

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 432ms/step - accuracy: 0.1679 - loss: 2.2343 - top-5-accuracy: 0.6218

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 430ms/step - accuracy: 0.1685 - loss: 2.2336 - top-5-accuracy: 0.6231

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 427ms/step - accuracy: 0.1693 - loss: 2.2326 - top-5-accuracy: 0.6246

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 424ms/step - accuracy: 0.1701 - loss: 2.2314 - top-5-accuracy: 0.6261

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 431ms/step - accuracy: 0.1709 - loss: 2.2306 - top-5-accuracy: 0.6272

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 437ms/step - accuracy: 0.1719 - loss: 2.2295 - top-5-accuracy: 0.6284

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 442ms/step - accuracy: 0.1728 - loss: 2.2287 - top-5-accuracy: 0.6294

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 447ms/step - accuracy: 0.1735 - loss: 2.2278 - top-5-accuracy: 0.6304

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 452ms/step - accuracy: 0.1740 - loss: 2.2269 - top-5-accuracy: 0.6315

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 456ms/step - accuracy: 0.1746 - loss: 2.2262 - top-5-accuracy: 0.6326

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 459ms/step - accuracy: 0.1749 - loss: 2.2257 - top-5-accuracy: 0.6334

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 463ms/step - accuracy: 0.1751 - loss: 2.2254 - top-5-accuracy: 0.6341

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 464ms/step - accuracy: 0.1754 - loss: 2.2250 - top-5-accuracy: 0.6348

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 456ms/step - accuracy: 0.1756 - loss: 2.2246 - top-5-accuracy: 0.6354

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 15s 492ms/step - accuracy: 0.1759 - loss: 2.2243 - top-5-accuracy: 0.6361 - val_accuracy: 0.1988 - val_loss: 2.2614 - val_top-5-accuracy: 0.6149


<div class="k-default-codeblock">
```
Epoch 4/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  14s 495ms/step - accuracy: 0.3438 - loss: 2.1334 - top-5-accuracy: 0.6250

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  14s 494ms/step - accuracy: 0.3125 - loss: 2.1371 - top-5-accuracy: 0.6406

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 493ms/step - accuracy: 0.2951 - loss: 2.1449 - top-5-accuracy: 0.6424

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  13s 492ms/step - accuracy: 0.2819 - loss: 2.1561 - top-5-accuracy: 0.6322

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  12s 464ms/step - accuracy: 0.2705 - loss: 2.1631 - top-5-accuracy: 0.6270

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  11s 445ms/step - accuracy: 0.2610 - loss: 2.1678 - top-5-accuracy: 0.6258

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  10s 433ms/step - accuracy: 0.2531 - loss: 2.1714 - top-5-accuracy: 0.6231

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 425ms/step - accuracy: 0.2468 - loss: 2.1729 - top-5-accuracy: 0.6238 

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 420ms/step - accuracy: 0.2418 - loss: 2.1736 - top-5-accuracy: 0.6267

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  8s 419ms/step - accuracy: 0.2389 - loss: 2.1739 - top-5-accuracy: 0.6309

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 414ms/step - accuracy: 0.2370 - loss: 2.1735 - top-5-accuracy: 0.6355

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  7s 412ms/step - accuracy: 0.2351 - loss: 2.1733 - top-5-accuracy: 0.6385

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 415ms/step - accuracy: 0.2340 - loss: 2.1725 - top-5-accuracy: 0.6427

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 418ms/step - accuracy: 0.2329 - loss: 2.1715 - top-5-accuracy: 0.6464

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 420ms/step - accuracy: 0.2318 - loss: 2.1706 - top-5-accuracy: 0.6499

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 419ms/step - accuracy: 0.2310 - loss: 2.1702 - top-5-accuracy: 0.6522

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 416ms/step - accuracy: 0.2305 - loss: 2.1699 - top-5-accuracy: 0.6540

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 413ms/step - accuracy: 0.2300 - loss: 2.1696 - top-5-accuracy: 0.6556

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 414ms/step - accuracy: 0.2296 - loss: 2.1690 - top-5-accuracy: 0.6574

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 416ms/step - accuracy: 0.2292 - loss: 2.1686 - top-5-accuracy: 0.6589

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 417ms/step - accuracy: 0.2288 - loss: 2.1682 - top-5-accuracy: 0.6604

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 418ms/step - accuracy: 0.2284 - loss: 2.1677 - top-5-accuracy: 0.6619

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 419ms/step - accuracy: 0.2282 - loss: 2.1670 - top-5-accuracy: 0.6636

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  2s 420ms/step - accuracy: 0.2279 - loss: 2.1664 - top-5-accuracy: 0.6651

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 420ms/step - accuracy: 0.2278 - loss: 2.1659 - top-5-accuracy: 0.6663

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 419ms/step - accuracy: 0.2275 - loss: 2.1655 - top-5-accuracy: 0.6673

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 418ms/step - accuracy: 0.2273 - loss: 2.1650 - top-5-accuracy: 0.6687

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 417ms/step - accuracy: 0.2271 - loss: 2.1646 - top-5-accuracy: 0.6698

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 418ms/step - accuracy: 0.2269 - loss: 2.1641 - top-5-accuracy: 0.6711

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 418ms/step - accuracy: 0.2268 - loss: 2.1637 - top-5-accuracy: 0.6723

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 411ms/step - accuracy: 0.2266 - loss: 2.1633 - top-5-accuracy: 0.6734

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 14s 436ms/step - accuracy: 0.2265 - loss: 2.1630 - top-5-accuracy: 0.6744 - val_accuracy: 0.2547 - val_loss: 2.2020 - val_top-5-accuracy: 0.6460


<div class="k-default-codeblock">
```
Epoch 5/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  11s 387ms/step - accuracy: 0.3125 - loss: 2.0208 - top-5-accuracy: 0.6562

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 368ms/step - accuracy: 0.2969 - loss: 2.0449 - top-5-accuracy: 0.6406

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 368ms/step - accuracy: 0.2812 - loss: 2.0540 - top-5-accuracy: 0.6389

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  10s 373ms/step - accuracy: 0.2676 - loss: 2.0639 - top-5-accuracy: 0.6432

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  9s 376ms/step - accuracy: 0.2616 - loss: 2.0696 - top-5-accuracy: 0.6508 

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  9s 387ms/step - accuracy: 0.2544 - loss: 2.0773 - top-5-accuracy: 0.6561

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  9s 393ms/step - accuracy: 0.2493 - loss: 2.0827 - top-5-accuracy: 0.6631

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  8s 390ms/step - accuracy: 0.2450 - loss: 2.0867 - top-5-accuracy: 0.6710

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  8s 387ms/step - accuracy: 0.2440 - loss: 2.0896 - top-5-accuracy: 0.6775

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  8s 387ms/step - accuracy: 0.2456 - loss: 2.0914 - top-5-accuracy: 0.6838

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  7s 389ms/step - accuracy: 0.2460 - loss: 2.0924 - top-5-accuracy: 0.6883

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  7s 395ms/step - accuracy: 0.2454 - loss: 2.0952 - top-5-accuracy: 0.6902

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 395ms/step - accuracy: 0.2450 - loss: 2.0968 - top-5-accuracy: 0.6922

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 396ms/step - accuracy: 0.2462 - loss: 2.0979 - top-5-accuracy: 0.6944

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 396ms/step - accuracy: 0.2467 - loss: 2.0991 - top-5-accuracy: 0.6963

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 396ms/step - accuracy: 0.2466 - loss: 2.1008 - top-5-accuracy: 0.6973

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 396ms/step - accuracy: 0.2467 - loss: 2.1022 - top-5-accuracy: 0.6978

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 396ms/step - accuracy: 0.2468 - loss: 2.1033 - top-5-accuracy: 0.6980

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 395ms/step - accuracy: 0.2467 - loss: 2.1044 - top-5-accuracy: 0.6980

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 394ms/step - accuracy: 0.2464 - loss: 2.1063 - top-5-accuracy: 0.6978

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  3s 394ms/step - accuracy: 0.2458 - loss: 2.1080 - top-5-accuracy: 0.6978

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 394ms/step - accuracy: 0.2450 - loss: 2.1096 - top-5-accuracy: 0.6981

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 393ms/step - accuracy: 0.2443 - loss: 2.1110 - top-5-accuracy: 0.6985

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  2s 394ms/step - accuracy: 0.2437 - loss: 2.1119 - top-5-accuracy: 0.6991

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 395ms/step - accuracy: 0.2430 - loss: 2.1126 - top-5-accuracy: 0.6998

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  1s 395ms/step - accuracy: 0.2423 - loss: 2.1133 - top-5-accuracy: 0.7003

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 396ms/step - accuracy: 0.2415 - loss: 2.1142 - top-5-accuracy: 0.7007

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 397ms/step - accuracy: 0.2409 - loss: 2.1150 - top-5-accuracy: 0.7010

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 397ms/step - accuracy: 0.2401 - loss: 2.1162 - top-5-accuracy: 0.7010

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 397ms/step - accuracy: 0.2394 - loss: 2.1173 - top-5-accuracy: 0.7010

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 389ms/step - accuracy: 0.2389 - loss: 2.1182 - top-5-accuracy: 0.7010

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 13s 411ms/step - accuracy: 0.2383 - loss: 2.1191 - top-5-accuracy: 0.7010 - val_accuracy: 0.2422 - val_loss: 2.0814 - val_top-5-accuracy: 0.7640


<div class="k-default-codeblock">
```
Epoch 6/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  11s 378ms/step - accuracy: 0.2812 - loss: 2.0495 - top-5-accuracy: 0.7188

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 472ms/step - accuracy: 0.2734 - loss: 2.0415 - top-5-accuracy: 0.7344

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  12s 451ms/step - accuracy: 0.2795 - loss: 2.0395 - top-5-accuracy: 0.7396

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  12s 447ms/step - accuracy: 0.2839 - loss: 2.0432 - top-5-accuracy: 0.7344

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  11s 455ms/step - accuracy: 0.2846 - loss: 2.0476 - top-5-accuracy: 0.7325

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 435ms/step - accuracy: 0.2823 - loss: 2.0538 - top-5-accuracy: 0.7293

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  10s 430ms/step - accuracy: 0.2770 - loss: 2.0609 - top-5-accuracy: 0.7272

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 435ms/step - accuracy: 0.2722 - loss: 2.0667 - top-5-accuracy: 0.7266

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 427ms/step - accuracy: 0.2686 - loss: 2.0706 - top-5-accuracy: 0.7254 

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  8s 427ms/step - accuracy: 0.2673 - loss: 2.0724 - top-5-accuracy: 0.7244

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 428ms/step - accuracy: 0.2650 - loss: 2.0747 - top-5-accuracy: 0.7228

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 425ms/step - accuracy: 0.2627 - loss: 2.0764 - top-5-accuracy: 0.7210

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 424ms/step - accuracy: 0.2609 - loss: 2.0778 - top-5-accuracy: 0.7199

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 423ms/step - accuracy: 0.2606 - loss: 2.0785 - top-5-accuracy: 0.7195

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 421ms/step - accuracy: 0.2598 - loss: 2.0793 - top-5-accuracy: 0.7192

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 422ms/step - accuracy: 0.2589 - loss: 2.0803 - top-5-accuracy: 0.7188

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 417ms/step - accuracy: 0.2580 - loss: 2.0810 - top-5-accuracy: 0.7189

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 415ms/step - accuracy: 0.2571 - loss: 2.0813 - top-5-accuracy: 0.7191

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 414ms/step - accuracy: 0.2567 - loss: 2.0815 - top-5-accuracy: 0.7190

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 415ms/step - accuracy: 0.2560 - loss: 2.0818 - top-5-accuracy: 0.7190

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 416ms/step - accuracy: 0.2553 - loss: 2.0818 - top-5-accuracy: 0.7195

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 416ms/step - accuracy: 0.2546 - loss: 2.0818 - top-5-accuracy: 0.7201

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 415ms/step - accuracy: 0.2540 - loss: 2.0814 - top-5-accuracy: 0.7210

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  2s 414ms/step - accuracy: 0.2535 - loss: 2.0811 - top-5-accuracy: 0.7217

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 416ms/step - accuracy: 0.2528 - loss: 2.0810 - top-5-accuracy: 0.7222

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 417ms/step - accuracy: 0.2522 - loss: 2.0808 - top-5-accuracy: 0.7229

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 419ms/step - accuracy: 0.2514 - loss: 2.0806 - top-5-accuracy: 0.7237

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 418ms/step - accuracy: 0.2507 - loss: 2.0805 - top-5-accuracy: 0.7245

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 417ms/step - accuracy: 0.2499 - loss: 2.0807 - top-5-accuracy: 0.7249

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 419ms/step - accuracy: 0.2491 - loss: 2.0810 - top-5-accuracy: 0.7250

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 412ms/step - accuracy: 0.2484 - loss: 2.0812 - top-5-accuracy: 0.7251

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 14s 446ms/step - accuracy: 0.2478 - loss: 2.0814 - top-5-accuracy: 0.7252 - val_accuracy: 0.3851 - val_loss: 2.0942 - val_top-5-accuracy: 0.7888


<div class="k-default-codeblock">
```
Epoch 7/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  14s 475ms/step - accuracy: 0.3438 - loss: 1.8934 - top-5-accuracy: 0.8750

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 466ms/step - accuracy: 0.3750 - loss: 1.9110 - top-5-accuracy: 0.8672

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 466ms/step - accuracy: 0.3646 - loss: 1.9371 - top-5-accuracy: 0.8524

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  12s 466ms/step - accuracy: 0.3496 - loss: 1.9605 - top-5-accuracy: 0.8307

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  12s 467ms/step - accuracy: 0.3372 - loss: 1.9751 - top-5-accuracy: 0.8171

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  11s 465ms/step - accuracy: 0.3279 - loss: 1.9840 - top-5-accuracy: 0.8068

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  11s 459ms/step - accuracy: 0.3193 - loss: 1.9911 - top-5-accuracy: 0.7993

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 454ms/step - accuracy: 0.3140 - loss: 1.9963 - top-5-accuracy: 0.7951

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 448ms/step - accuracy: 0.3096 - loss: 2.0016 - top-5-accuracy: 0.7916 

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  9s 446ms/step - accuracy: 0.3068 - loss: 2.0045 - top-5-accuracy: 0.7900

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 445ms/step - accuracy: 0.3050 - loss: 2.0060 - top-5-accuracy: 0.7892

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 444ms/step - accuracy: 0.3041 - loss: 2.0072 - top-5-accuracy: 0.7889

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 441ms/step - accuracy: 0.3042 - loss: 2.0074 - top-5-accuracy: 0.7895

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 435ms/step - accuracy: 0.3049 - loss: 2.0074 - top-5-accuracy: 0.7898

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 431ms/step - accuracy: 0.3064 - loss: 2.0070 - top-5-accuracy: 0.7904

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 430ms/step - accuracy: 0.3070 - loss: 2.0072 - top-5-accuracy: 0.7908

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 426ms/step - accuracy: 0.3079 - loss: 2.0073 - top-5-accuracy: 0.7911

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 425ms/step - accuracy: 0.3084 - loss: 2.0076 - top-5-accuracy: 0.7912

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 427ms/step - accuracy: 0.3089 - loss: 2.0082 - top-5-accuracy: 0.7909

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 429ms/step - accuracy: 0.3096 - loss: 2.0080 - top-5-accuracy: 0.7908

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 431ms/step - accuracy: 0.3101 - loss: 2.0083 - top-5-accuracy: 0.7907

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 433ms/step - accuracy: 0.3102 - loss: 2.0086 - top-5-accuracy: 0.7906

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 434ms/step - accuracy: 0.3103 - loss: 2.0086 - top-5-accuracy: 0.7906

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 436ms/step - accuracy: 0.3104 - loss: 2.0086 - top-5-accuracy: 0.7908

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 437ms/step - accuracy: 0.3103 - loss: 2.0084 - top-5-accuracy: 0.7910

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 438ms/step - accuracy: 0.3100 - loss: 2.0085 - top-5-accuracy: 0.7913

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 439ms/step - accuracy: 0.3096 - loss: 2.0087 - top-5-accuracy: 0.7916

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 440ms/step - accuracy: 0.3093 - loss: 2.0089 - top-5-accuracy: 0.7917

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 441ms/step - accuracy: 0.3090 - loss: 2.0091 - top-5-accuracy: 0.7917

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 441ms/step - accuracy: 0.3087 - loss: 2.0094 - top-5-accuracy: 0.7917

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 433ms/step - accuracy: 0.3085 - loss: 2.0094 - top-5-accuracy: 0.7917

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 14s 465ms/step - accuracy: 0.3083 - loss: 2.0094 - top-5-accuracy: 0.7917 - val_accuracy: 0.4161 - val_loss: 1.9760 - val_top-5-accuracy: 0.8571


<div class="k-default-codeblock">
```
Epoch 8/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  11s 393ms/step - accuracy: 0.3438 - loss: 2.0636 - top-5-accuracy: 0.7500

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 375ms/step - accuracy: 0.3906 - loss: 2.0196 - top-5-accuracy: 0.7500

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 391ms/step - accuracy: 0.3889 - loss: 2.0066 - top-5-accuracy: 0.7535

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  11s 410ms/step - accuracy: 0.3796 - loss: 2.0025 - top-5-accuracy: 0.7624

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 419ms/step - accuracy: 0.3736 - loss: 1.9935 - top-5-accuracy: 0.7736

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 425ms/step - accuracy: 0.3661 - loss: 1.9870 - top-5-accuracy: 0.7810

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  10s 429ms/step - accuracy: 0.3610 - loss: 1.9802 - top-5-accuracy: 0.7868

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 432ms/step - accuracy: 0.3554 - loss: 1.9758 - top-5-accuracy: 0.7919 

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 434ms/step - accuracy: 0.3518 - loss: 1.9705 - top-5-accuracy: 0.7973

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  9s 435ms/step - accuracy: 0.3475 - loss: 1.9667 - top-5-accuracy: 0.8016

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 438ms/step - accuracy: 0.3454 - loss: 1.9636 - top-5-accuracy: 0.8052

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 439ms/step - accuracy: 0.3435 - loss: 1.9613 - top-5-accuracy: 0.8078

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 440ms/step - accuracy: 0.3417 - loss: 1.9602 - top-5-accuracy: 0.8094

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 441ms/step - accuracy: 0.3406 - loss: 1.9590 - top-5-accuracy: 0.8108

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 442ms/step - accuracy: 0.3399 - loss: 1.9574 - top-5-accuracy: 0.8117

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 442ms/step - accuracy: 0.3391 - loss: 1.9565 - top-5-accuracy: 0.8121

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 443ms/step - accuracy: 0.3384 - loss: 1.9562 - top-5-accuracy: 0.8118

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 444ms/step - accuracy: 0.3379 - loss: 1.9556 - top-5-accuracy: 0.8120

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 444ms/step - accuracy: 0.3370 - loss: 1.9557 - top-5-accuracy: 0.8121

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 445ms/step - accuracy: 0.3359 - loss: 1.9558 - top-5-accuracy: 0.8123

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 445ms/step - accuracy: 0.3349 - loss: 1.9560 - top-5-accuracy: 0.8126

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 445ms/step - accuracy: 0.3337 - loss: 1.9564 - top-5-accuracy: 0.8131

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 442ms/step - accuracy: 0.3328 - loss: 1.9563 - top-5-accuracy: 0.8139

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 439ms/step - accuracy: 0.3317 - loss: 1.9562 - top-5-accuracy: 0.8146

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 436ms/step - accuracy: 0.3307 - loss: 1.9561 - top-5-accuracy: 0.8151

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 434ms/step - accuracy: 0.3297 - loss: 1.9558 - top-5-accuracy: 0.8156

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 431ms/step - accuracy: 0.3289 - loss: 1.9555 - top-5-accuracy: 0.8160

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 429ms/step - accuracy: 0.3280 - loss: 1.9555 - top-5-accuracy: 0.8163

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 427ms/step - accuracy: 0.3272 - loss: 1.9555 - top-5-accuracy: 0.8163

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 426ms/step - accuracy: 0.3262 - loss: 1.9556 - top-5-accuracy: 0.8163

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 417ms/step - accuracy: 0.3253 - loss: 1.9556 - top-5-accuracy: 0.8163

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 14s 441ms/step - accuracy: 0.3245 - loss: 1.9557 - top-5-accuracy: 0.8163 - val_accuracy: 0.3292 - val_loss: 1.9502 - val_top-5-accuracy: 0.8634


<div class="k-default-codeblock">
```
Epoch 9/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  11s 392ms/step - accuracy: 0.4375 - loss: 1.9896 - top-5-accuracy: 0.7500

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  12s 427ms/step - accuracy: 0.3984 - loss: 2.0040 - top-5-accuracy: 0.7266

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  11s 413ms/step - accuracy: 0.3906 - loss: 1.9890 - top-5-accuracy: 0.7309

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  10s 401ms/step - accuracy: 0.3906 - loss: 1.9850 - top-5-accuracy: 0.7337

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 393ms/step - accuracy: 0.3938 - loss: 1.9737 - top-5-accuracy: 0.7357

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  9s 392ms/step - accuracy: 0.3898 - loss: 1.9704 - top-5-accuracy: 0.7381 

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  9s 396ms/step - accuracy: 0.3870 - loss: 1.9657 - top-5-accuracy: 0.7411

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 399ms/step - accuracy: 0.3840 - loss: 1.9629 - top-5-accuracy: 0.7451

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  8s 401ms/step - accuracy: 0.3811 - loss: 1.9608 - top-5-accuracy: 0.7488

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  8s 402ms/step - accuracy: 0.3786 - loss: 1.9579 - top-5-accuracy: 0.7533

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 401ms/step - accuracy: 0.3775 - loss: 1.9541 - top-5-accuracy: 0.7579

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  7s 401ms/step - accuracy: 0.3767 - loss: 1.9504 - top-5-accuracy: 0.7624

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 405ms/step - accuracy: 0.3763 - loss: 1.9462 - top-5-accuracy: 0.7670

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 408ms/step - accuracy: 0.3759 - loss: 1.9419 - top-5-accuracy: 0.7717

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 411ms/step - accuracy: 0.3746 - loss: 1.9395 - top-5-accuracy: 0.7751

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 413ms/step - accuracy: 0.3732 - loss: 1.9378 - top-5-accuracy: 0.7777

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 415ms/step - accuracy: 0.3713 - loss: 1.9372 - top-5-accuracy: 0.7795

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 415ms/step - accuracy: 0.3697 - loss: 1.9362 - top-5-accuracy: 0.7812

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 414ms/step - accuracy: 0.3678 - loss: 1.9354 - top-5-accuracy: 0.7828

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 413ms/step - accuracy: 0.3661 - loss: 1.9345 - top-5-accuracy: 0.7843

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 411ms/step - accuracy: 0.3644 - loss: 1.9339 - top-5-accuracy: 0.7856

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 412ms/step - accuracy: 0.3627 - loss: 1.9339 - top-5-accuracy: 0.7865

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 413ms/step - accuracy: 0.3613 - loss: 1.9339 - top-5-accuracy: 0.7874

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  2s 412ms/step - accuracy: 0.3597 - loss: 1.9340 - top-5-accuracy: 0.7884

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 410ms/step - accuracy: 0.3584 - loss: 1.9339 - top-5-accuracy: 0.7894

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 409ms/step - accuracy: 0.3572 - loss: 1.9335 - top-5-accuracy: 0.7904

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 409ms/step - accuracy: 0.3558 - loss: 1.9341 - top-5-accuracy: 0.7910

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 408ms/step - accuracy: 0.3546 - loss: 1.9345 - top-5-accuracy: 0.7914

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 407ms/step - accuracy: 0.3533 - loss: 1.9350 - top-5-accuracy: 0.7917

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 406ms/step - accuracy: 0.3521 - loss: 1.9354 - top-5-accuracy: 0.7919

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 398ms/step - accuracy: 0.3509 - loss: 1.9357 - top-5-accuracy: 0.7921

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 13s 424ms/step - accuracy: 0.3498 - loss: 1.9360 - top-5-accuracy: 0.7923 - val_accuracy: 0.3602 - val_loss: 1.8967 - val_top-5-accuracy: 0.7950


<div class="k-default-codeblock">
```
Epoch 10/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  12s 404ms/step - accuracy: 0.3750 - loss: 1.9534 - top-5-accuracy: 0.7188

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 364ms/step - accuracy: 0.3438 - loss: 1.9377 - top-5-accuracy: 0.7344

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  10s 377ms/step - accuracy: 0.3264 - loss: 1.9257 - top-5-accuracy: 0.7500

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  10s 388ms/step - accuracy: 0.3132 - loss: 1.9324 - top-5-accuracy: 0.7461

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  11s 425ms/step - accuracy: 0.3043 - loss: 1.9409 - top-5-accuracy: 0.7469

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  10s 416ms/step - accuracy: 0.3004 - loss: 1.9409 - top-5-accuracy: 0.7500

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  9s 403ms/step - accuracy: 0.2977 - loss: 1.9392 - top-5-accuracy: 0.7551 

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  9s 400ms/step - accuracy: 0.2956 - loss: 1.9362 - top-5-accuracy: 0.7608

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  8s 397ms/step - accuracy: 0.2937 - loss: 1.9326 - top-5-accuracy: 0.7654

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  8s 395ms/step - accuracy: 0.2927 - loss: 1.9292 - top-5-accuracy: 0.7698

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  7s 394ms/step - accuracy: 0.2930 - loss: 1.9269 - top-5-accuracy: 0.7729

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  7s 392ms/step - accuracy: 0.2933 - loss: 1.9247 - top-5-accuracy: 0.7762

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  7s 393ms/step - accuracy: 0.2933 - loss: 1.9223 - top-5-accuracy: 0.7797

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 397ms/step - accuracy: 0.2928 - loss: 1.9206 - top-5-accuracy: 0.7827

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  6s 399ms/step - accuracy: 0.2924 - loss: 1.9200 - top-5-accuracy: 0.7848

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 402ms/step - accuracy: 0.2920 - loss: 1.9197 - top-5-accuracy: 0.7869

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  5s 404ms/step - accuracy: 0.2914 - loss: 1.9201 - top-5-accuracy: 0.7885

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  5s 404ms/step - accuracy: 0.2911 - loss: 1.9203 - top-5-accuracy: 0.7901

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 403ms/step - accuracy: 0.2905 - loss: 1.9209 - top-5-accuracy: 0.7914

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  4s 401ms/step - accuracy: 0.2902 - loss: 1.9211 - top-5-accuracy: 0.7927

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 402ms/step - accuracy: 0.2896 - loss: 1.9215 - top-5-accuracy: 0.7941

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 405ms/step - accuracy: 0.2890 - loss: 1.9218 - top-5-accuracy: 0.7954

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 408ms/step - accuracy: 0.2884 - loss: 1.9221 - top-5-accuracy: 0.7968

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  2s 410ms/step - accuracy: 0.2878 - loss: 1.9223 - top-5-accuracy: 0.7980

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 412ms/step - accuracy: 0.2876 - loss: 1.9223 - top-5-accuracy: 0.7990

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 415ms/step - accuracy: 0.2874 - loss: 1.9221 - top-5-accuracy: 0.7999

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 417ms/step - accuracy: 0.2872 - loss: 1.9223 - top-5-accuracy: 0.8006

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 418ms/step - accuracy: 0.2870 - loss: 1.9225 - top-5-accuracy: 0.8012

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 420ms/step - accuracy: 0.2870 - loss: 1.9224 - top-5-accuracy: 0.8017

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 422ms/step - accuracy: 0.2871 - loss: 1.9224 - top-5-accuracy: 0.8022

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 414ms/step - accuracy: 0.2872 - loss: 1.9223 - top-5-accuracy: 0.8027

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 14s 445ms/step - accuracy: 0.2873 - loss: 1.9222 - top-5-accuracy: 0.8032 - val_accuracy: 0.3602 - val_loss: 1.8630 - val_top-5-accuracy: 0.7640


<div class="k-default-codeblock">
```
Epoch 11/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  12s 408ms/step - accuracy: 0.3125 - loss: 1.9669 - top-5-accuracy: 0.6875

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  11s 410ms/step - accuracy: 0.3438 - loss: 1.9314 - top-5-accuracy: 0.7109

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  12s 440ms/step - accuracy: 0.3681 - loss: 1.9161 - top-5-accuracy: 0.7135

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  16s 610ms/step - accuracy: 0.3698 - loss: 1.9206 - top-5-accuracy: 0.7070

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  21s 815ms/step - accuracy: 0.3658 - loss: 1.9284 - top-5-accuracy: 0.7031

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  18s 754ms/step - accuracy: 0.3613 - loss: 1.9327 - top-5-accuracy: 0.7014

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  17s 709ms/step - accuracy: 0.3601 - loss: 1.9323 - top-5-accuracy: 0.7032

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  15s 682ms/step - accuracy: 0.3614 - loss: 1.9297 - top-5-accuracy: 0.7057

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  14s 657ms/step - accuracy: 0.3626 - loss: 1.9270 - top-5-accuracy: 0.7087

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  13s 637ms/step - accuracy: 0.3626 - loss: 1.9248 - top-5-accuracy: 0.7115

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  12s 622ms/step - accuracy: 0.3616 - loss: 1.9232 - top-5-accuracy: 0.7148

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 610ms/step - accuracy: 0.3606 - loss: 1.9214 - top-5-accuracy: 0.7186

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 598ms/step - accuracy: 0.3600 - loss: 1.9197 - top-5-accuracy: 0.7223

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  10s 592ms/step - accuracy: 0.3596 - loss: 1.9171 - top-5-accuracy: 0.7265

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 589ms/step - accuracy: 0.3593 - loss: 1.9142 - top-5-accuracy: 0.7306 

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 586ms/step - accuracy: 0.3588 - loss: 1.9121 - top-5-accuracy: 0.7336

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 584ms/step - accuracy: 0.3579 - loss: 1.9104 - top-5-accuracy: 0.7360

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 581ms/step - accuracy: 0.3566 - loss: 1.9091 - top-5-accuracy: 0.7379

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 579ms/step - accuracy: 0.3558 - loss: 1.9076 - top-5-accuracy: 0.7398

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 577ms/step - accuracy: 0.3549 - loss: 1.9062 - top-5-accuracy: 0.7418

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 576ms/step - accuracy: 0.3541 - loss: 1.9047 - top-5-accuracy: 0.7439

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 574ms/step - accuracy: 0.3531 - loss: 1.9035 - top-5-accuracy: 0.7459

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 573ms/step - accuracy: 0.3523 - loss: 1.9021 - top-5-accuracy: 0.7480

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  4s 572ms/step - accuracy: 0.3515 - loss: 1.9006 - top-5-accuracy: 0.7502

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 571ms/step - accuracy: 0.3512 - loss: 1.8988 - top-5-accuracy: 0.7523

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 570ms/step - accuracy: 0.3508 - loss: 1.8972 - top-5-accuracy: 0.7542

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 569ms/step - accuracy: 0.3502 - loss: 1.8959 - top-5-accuracy: 0.7561

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 568ms/step - accuracy: 0.3498 - loss: 1.8947 - top-5-accuracy: 0.7579

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 567ms/step - accuracy: 0.3495 - loss: 1.8934 - top-5-accuracy: 0.7597

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 567ms/step - accuracy: 0.3494 - loss: 1.8921 - top-5-accuracy: 0.7615

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 555ms/step - accuracy: 0.3493 - loss: 1.8905 - top-5-accuracy: 0.7633

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 599ms/step - accuracy: 0.3493 - loss: 1.8891 - top-5-accuracy: 0.7650 - val_accuracy: 0.3478 - val_loss: 1.7683 - val_top-5-accuracy: 0.8882


<div class="k-default-codeblock">
```
Epoch 12/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 569ms/step - accuracy: 0.4062 - loss: 1.7123 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.3906 - loss: 1.7463 - top-5-accuracy: 0.9141

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 542ms/step - accuracy: 0.3681 - loss: 1.7750 - top-5-accuracy: 0.9045

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.3698 - loss: 1.7877 - top-5-accuracy: 0.8913

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.3783 - loss: 1.7912 - top-5-accuracy: 0.8830

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.3804 - loss: 1.7961 - top-5-accuracy: 0.8747

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.3847 - loss: 1.7949 - top-5-accuracy: 0.8684

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.3879 - loss: 1.7913 - top-5-accuracy: 0.8653

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.3888 - loss: 1.7896 - top-5-accuracy: 0.8622

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.3890 - loss: 1.7884 - top-5-accuracy: 0.8597

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.3872 - loss: 1.7883 - top-5-accuracy: 0.8585

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.3864 - loss: 1.7863 - top-5-accuracy: 0.8586

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.3874 - loss: 1.7834 - top-5-accuracy: 0.8593 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 546ms/step - accuracy: 0.3882 - loss: 1.7810 - top-5-accuracy: 0.8596

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 547ms/step - accuracy: 0.3890 - loss: 1.7793 - top-5-accuracy: 0.8595

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 547ms/step - accuracy: 0.3897 - loss: 1.7784 - top-5-accuracy: 0.8591

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 547ms/step - accuracy: 0.3900 - loss: 1.7785 - top-5-accuracy: 0.8587

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 547ms/step - accuracy: 0.3899 - loss: 1.7789 - top-5-accuracy: 0.8583

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.3900 - loss: 1.7794 - top-5-accuracy: 0.8577

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.3900 - loss: 1.7794 - top-5-accuracy: 0.8575

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.3901 - loss: 1.7792 - top-5-accuracy: 0.8574

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.3900 - loss: 1.7788 - top-5-accuracy: 0.8574

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.3898 - loss: 1.7787 - top-5-accuracy: 0.8575

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.3894 - loss: 1.7793 - top-5-accuracy: 0.8574

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.3892 - loss: 1.7796 - top-5-accuracy: 0.8574

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.3889 - loss: 1.7796 - top-5-accuracy: 0.8576

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.3883 - loss: 1.7798 - top-5-accuracy: 0.8578

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.3878 - loss: 1.7800 - top-5-accuracy: 0.8579

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.3876 - loss: 1.7797 - top-5-accuracy: 0.8580

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.3872 - loss: 1.7798 - top-5-accuracy: 0.8581

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.3868 - loss: 1.7800 - top-5-accuracy: 0.8582

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.3864 - loss: 1.7802 - top-5-accuracy: 0.8583 - val_accuracy: 0.3727 - val_loss: 1.7841 - val_top-5-accuracy: 0.8944


<div class="k-default-codeblock">
```
Epoch 13/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 557ms/step - accuracy: 0.4062 - loss: 1.6497 - top-5-accuracy: 0.8750

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 542ms/step - accuracy: 0.4375 - loss: 1.6246 - top-5-accuracy: 0.8750

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 541ms/step - accuracy: 0.4271 - loss: 1.6759 - top-5-accuracy: 0.8576

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 540ms/step - accuracy: 0.4199 - loss: 1.6992 - top-5-accuracy: 0.8483

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 541ms/step - accuracy: 0.4134 - loss: 1.7162 - top-5-accuracy: 0.8461

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 542ms/step - accuracy: 0.4088 - loss: 1.7224 - top-5-accuracy: 0.8449

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  12s 542ms/step - accuracy: 0.4071 - loss: 1.7263 - top-5-accuracy: 0.8447

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 542ms/step - accuracy: 0.4036 - loss: 1.7302 - top-5-accuracy: 0.8456

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.4004 - loss: 1.7320 - top-5-accuracy: 0.8473

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.3966 - loss: 1.7339 - top-5-accuracy: 0.8485

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.3926 - loss: 1.7367 - top-5-accuracy: 0.8491

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.3900 - loss: 1.7387 - top-5-accuracy: 0.8489

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 543ms/step - accuracy: 0.3893 - loss: 1.7394 - top-5-accuracy: 0.8492 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 543ms/step - accuracy: 0.3881 - loss: 1.7403 - top-5-accuracy: 0.8499

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 543ms/step - accuracy: 0.3876 - loss: 1.7407 - top-5-accuracy: 0.8506

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 543ms/step - accuracy: 0.3865 - loss: 1.7422 - top-5-accuracy: 0.8505

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 543ms/step - accuracy: 0.3851 - loss: 1.7442 - top-5-accuracy: 0.8500

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 543ms/step - accuracy: 0.3838 - loss: 1.7457 - top-5-accuracy: 0.8497

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 544ms/step - accuracy: 0.3829 - loss: 1.7466 - top-5-accuracy: 0.8497

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 544ms/step - accuracy: 0.3820 - loss: 1.7473 - top-5-accuracy: 0.8497

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 543ms/step - accuracy: 0.3812 - loss: 1.7483 - top-5-accuracy: 0.8497

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 543ms/step - accuracy: 0.3805 - loss: 1.7492 - top-5-accuracy: 0.8497

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.3800 - loss: 1.7497 - top-5-accuracy: 0.8499

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.3794 - loss: 1.7502 - top-5-accuracy: 0.8503

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 544ms/step - accuracy: 0.3792 - loss: 1.7503 - top-5-accuracy: 0.8508

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 544ms/step - accuracy: 0.3791 - loss: 1.7502 - top-5-accuracy: 0.8512

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 544ms/step - accuracy: 0.3790 - loss: 1.7503 - top-5-accuracy: 0.8515

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.3789 - loss: 1.7504 - top-5-accuracy: 0.8516

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.3787 - loss: 1.7506 - top-5-accuracy: 0.8517

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 544ms/step - accuracy: 0.3787 - loss: 1.7506 - top-5-accuracy: 0.8519

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.3786 - loss: 1.7505 - top-5-accuracy: 0.8521

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.3785 - loss: 1.7505 - top-5-accuracy: 0.8523 - val_accuracy: 0.5280 - val_loss: 1.6127 - val_top-5-accuracy: 0.9255


<div class="k-default-codeblock">
```
Epoch 14/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 583ms/step - accuracy: 0.5625 - loss: 1.6991 - top-5-accuracy: 0.8438

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 532ms/step - accuracy: 0.5234 - loss: 1.7314 - top-5-accuracy: 0.8203

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 551ms/step - accuracy: 0.4878 - loss: 1.7453 - top-5-accuracy: 0.8177

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  15s 556ms/step - accuracy: 0.4635 - loss: 1.7440 - top-5-accuracy: 0.8203

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 564ms/step - accuracy: 0.4521 - loss: 1.7352 - top-5-accuracy: 0.8238

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 561ms/step - accuracy: 0.4436 - loss: 1.7310 - top-5-accuracy: 0.8288

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 564ms/step - accuracy: 0.4376 - loss: 1.7286 - top-5-accuracy: 0.8310

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  13s 580ms/step - accuracy: 0.4327 - loss: 1.7266 - top-5-accuracy: 0.8326

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 581ms/step - accuracy: 0.4290 - loss: 1.7247 - top-5-accuracy: 0.8350

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  12s 577ms/step - accuracy: 0.4264 - loss: 1.7217 - top-5-accuracy: 0.8377

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 573ms/step - accuracy: 0.4238 - loss: 1.7203 - top-5-accuracy: 0.8398

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 571ms/step - accuracy: 0.4228 - loss: 1.7187 - top-5-accuracy: 0.8423

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 569ms/step - accuracy: 0.4221 - loss: 1.7161 - top-5-accuracy: 0.8452

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 567ms/step - accuracy: 0.4211 - loss: 1.7134 - top-5-accuracy: 0.8481 

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 565ms/step - accuracy: 0.4205 - loss: 1.7112 - top-5-accuracy: 0.8503

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 563ms/step - accuracy: 0.4194 - loss: 1.7097 - top-5-accuracy: 0.8520

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 562ms/step - accuracy: 0.4177 - loss: 1.7096 - top-5-accuracy: 0.8527

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 561ms/step - accuracy: 0.4160 - loss: 1.7106 - top-5-accuracy: 0.8530

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 561ms/step - accuracy: 0.4145 - loss: 1.7115 - top-5-accuracy: 0.8533

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 560ms/step - accuracy: 0.4133 - loss: 1.7123 - top-5-accuracy: 0.8533

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 559ms/step - accuracy: 0.4123 - loss: 1.7131 - top-5-accuracy: 0.8532

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 558ms/step - accuracy: 0.4111 - loss: 1.7148 - top-5-accuracy: 0.8527

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 558ms/step - accuracy: 0.4100 - loss: 1.7162 - top-5-accuracy: 0.8523

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 558ms/step - accuracy: 0.4090 - loss: 1.7176 - top-5-accuracy: 0.8520

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 557ms/step - accuracy: 0.4078 - loss: 1.7191 - top-5-accuracy: 0.8517

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 557ms/step - accuracy: 0.4065 - loss: 1.7205 - top-5-accuracy: 0.8515

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 556ms/step - accuracy: 0.4052 - loss: 1.7217 - top-5-accuracy: 0.8515

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 556ms/step - accuracy: 0.4042 - loss: 1.7224 - top-5-accuracy: 0.8516

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 555ms/step - accuracy: 0.4033 - loss: 1.7229 - top-5-accuracy: 0.8519

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 555ms/step - accuracy: 0.4026 - loss: 1.7232 - top-5-accuracy: 0.8522

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 544ms/step - accuracy: 0.4020 - loss: 1.7235 - top-5-accuracy: 0.8525

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 587ms/step - accuracy: 0.4014 - loss: 1.7238 - top-5-accuracy: 0.8528 - val_accuracy: 0.4783 - val_loss: 1.6619 - val_top-5-accuracy: 0.8696


<div class="k-default-codeblock">
```
Epoch 15/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 562ms/step - accuracy: 0.4375 - loss: 1.7202 - top-5-accuracy: 0.9062

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.4609 - loss: 1.7300 - top-5-accuracy: 0.8906

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 550ms/step - accuracy: 0.4705 - loss: 1.7096 - top-5-accuracy: 0.8819

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 549ms/step - accuracy: 0.4661 - loss: 1.7012 - top-5-accuracy: 0.8822

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 548ms/step - accuracy: 0.4592 - loss: 1.6967 - top-5-accuracy: 0.8807

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 548ms/step - accuracy: 0.4530 - loss: 1.6901 - top-5-accuracy: 0.8824

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.4520 - loss: 1.6791 - top-5-accuracy: 0.8852

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.4497 - loss: 1.6729 - top-5-accuracy: 0.8863

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.4491 - loss: 1.6684 - top-5-accuracy: 0.8882

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.4492 - loss: 1.6643 - top-5-accuracy: 0.8893

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.4497 - loss: 1.6602 - top-5-accuracy: 0.8901

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.4506 - loss: 1.6561 - top-5-accuracy: 0.8910

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.4509 - loss: 1.6528 - top-5-accuracy: 0.8916 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.4511 - loss: 1.6503 - top-5-accuracy: 0.8916

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.4509 - loss: 1.6482 - top-5-accuracy: 0.8916

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.4503 - loss: 1.6466 - top-5-accuracy: 0.8919

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.4491 - loss: 1.6459 - top-5-accuracy: 0.8917

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 544ms/step - accuracy: 0.4477 - loss: 1.6462 - top-5-accuracy: 0.8916

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 544ms/step - accuracy: 0.4462 - loss: 1.6470 - top-5-accuracy: 0.8912

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 544ms/step - accuracy: 0.4450 - loss: 1.6476 - top-5-accuracy: 0.8910

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.4438 - loss: 1.6478 - top-5-accuracy: 0.8910

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.4423 - loss: 1.6483 - top-5-accuracy: 0.8911

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.4410 - loss: 1.6491 - top-5-accuracy: 0.8913

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.4397 - loss: 1.6499 - top-5-accuracy: 0.8915

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 544ms/step - accuracy: 0.4387 - loss: 1.6507 - top-5-accuracy: 0.8917

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 544ms/step - accuracy: 0.4376 - loss: 1.6515 - top-5-accuracy: 0.8919

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 544ms/step - accuracy: 0.4368 - loss: 1.6522 - top-5-accuracy: 0.8920

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.4361 - loss: 1.6525 - top-5-accuracy: 0.8922

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.4353 - loss: 1.6527 - top-5-accuracy: 0.8925

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 544ms/step - accuracy: 0.4347 - loss: 1.6525 - top-5-accuracy: 0.8929

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.4342 - loss: 1.6527 - top-5-accuracy: 0.8933

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.4336 - loss: 1.6528 - top-5-accuracy: 0.8936 - val_accuracy: 0.4596 - val_loss: 1.5849 - val_top-5-accuracy: 0.8820


<div class="k-default-codeblock">
```
Epoch 16/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 552ms/step - accuracy: 0.4375 - loss: 1.6735 - top-5-accuracy: 0.8750

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.4609 - loss: 1.6322 - top-5-accuracy: 0.8672

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.4878 - loss: 1.6067 - top-5-accuracy: 0.8698

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.4909 - loss: 1.6071 - top-5-accuracy: 0.8711

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 543ms/step - accuracy: 0.4865 - loss: 1.6084 - top-5-accuracy: 0.8719

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.4792 - loss: 1.6134 - top-5-accuracy: 0.8724

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.4751 - loss: 1.6113 - top-5-accuracy: 0.8740

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 543ms/step - accuracy: 0.4704 - loss: 1.6097 - top-5-accuracy: 0.8761

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.4668 - loss: 1.6090 - top-5-accuracy: 0.8787

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.4629 - loss: 1.6085 - top-5-accuracy: 0.8811

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.4609 - loss: 1.6062 - top-5-accuracy: 0.8834

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.4593 - loss: 1.6032 - top-5-accuracy: 0.8860

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 544ms/step - accuracy: 0.4580 - loss: 1.6006 - top-5-accuracy: 0.8879 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.4575 - loss: 1.5967 - top-5-accuracy: 0.8900

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.4570 - loss: 1.5941 - top-5-accuracy: 0.8916

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.4562 - loss: 1.5923 - top-5-accuracy: 0.8930

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.4550 - loss: 1.5914 - top-5-accuracy: 0.8943

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.4538 - loss: 1.5909 - top-5-accuracy: 0.8953

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.4530 - loss: 1.5900 - top-5-accuracy: 0.8962

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.4522 - loss: 1.5895 - top-5-accuracy: 0.8971

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.4512 - loss: 1.5891 - top-5-accuracy: 0.8979

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.4503 - loss: 1.5891 - top-5-accuracy: 0.8986

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.4498 - loss: 1.5886 - top-5-accuracy: 0.8994

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.4492 - loss: 1.5878 - top-5-accuracy: 0.9001

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.4488 - loss: 1.5868 - top-5-accuracy: 0.9009

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.4482 - loss: 1.5859 - top-5-accuracy: 0.9016

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.4475 - loss: 1.5852 - top-5-accuracy: 0.9022

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.4469 - loss: 1.5845 - top-5-accuracy: 0.9028

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.4465 - loss: 1.5837 - top-5-accuracy: 0.9035

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.4463 - loss: 1.5828 - top-5-accuracy: 0.9041

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.4461 - loss: 1.5816 - top-5-accuracy: 0.9046

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.4459 - loss: 1.5805 - top-5-accuracy: 0.9052 - val_accuracy: 0.5031 - val_loss: 1.5402 - val_top-5-accuracy: 0.8820


<div class="k-default-codeblock">
```
Epoch 17/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 551ms/step - accuracy: 0.5312 - loss: 1.6829 - top-5-accuracy: 0.7500

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.5234 - loss: 1.7026 - top-5-accuracy: 0.7578

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 543ms/step - accuracy: 0.5156 - loss: 1.6945 - top-5-accuracy: 0.7656

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 543ms/step - accuracy: 0.5078 - loss: 1.6801 - top-5-accuracy: 0.7812

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 543ms/step - accuracy: 0.5025 - loss: 1.6675 - top-5-accuracy: 0.7937

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.4969 - loss: 1.6607 - top-5-accuracy: 0.8030

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.4903 - loss: 1.6566 - top-5-accuracy: 0.8120

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 544ms/step - accuracy: 0.4852 - loss: 1.6522 - top-5-accuracy: 0.8189

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.4799 - loss: 1.6471 - top-5-accuracy: 0.8247

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.4750 - loss: 1.6426 - top-5-accuracy: 0.8297

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.4719 - loss: 1.6370 - top-5-accuracy: 0.8341

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.4688 - loss: 1.6328 - top-5-accuracy: 0.8380

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 543ms/step - accuracy: 0.4673 - loss: 1.6278 - top-5-accuracy: 0.8419 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 544ms/step - accuracy: 0.4663 - loss: 1.6228 - top-5-accuracy: 0.8456

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 544ms/step - accuracy: 0.4655 - loss: 1.6188 - top-5-accuracy: 0.8482

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 544ms/step - accuracy: 0.4642 - loss: 1.6159 - top-5-accuracy: 0.8503

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 544ms/step - accuracy: 0.4626 - loss: 1.6133 - top-5-accuracy: 0.8523

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 544ms/step - accuracy: 0.4612 - loss: 1.6109 - top-5-accuracy: 0.8538

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 544ms/step - accuracy: 0.4597 - loss: 1.6086 - top-5-accuracy: 0.8552

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 544ms/step - accuracy: 0.4582 - loss: 1.6071 - top-5-accuracy: 0.8563

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.4567 - loss: 1.6055 - top-5-accuracy: 0.8576

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.4552 - loss: 1.6040 - top-5-accuracy: 0.8589

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.4540 - loss: 1.6023 - top-5-accuracy: 0.8602

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.4529 - loss: 1.6009 - top-5-accuracy: 0.8616

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.4520 - loss: 1.5993 - top-5-accuracy: 0.8628

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.4513 - loss: 1.5978 - top-5-accuracy: 0.8641

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.4508 - loss: 1.5960 - top-5-accuracy: 0.8653

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.4503 - loss: 1.5940 - top-5-accuracy: 0.8666

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.4501 - loss: 1.5921 - top-5-accuracy: 0.8678

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.4500 - loss: 1.5902 - top-5-accuracy: 0.8689

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.4499 - loss: 1.5888 - top-5-accuracy: 0.8699

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.4497 - loss: 1.5875 - top-5-accuracy: 0.8709 - val_accuracy: 0.5155 - val_loss: 1.3706 - val_top-5-accuracy: 0.9379


<div class="k-default-codeblock">
```
Epoch 18/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 556ms/step - accuracy: 0.4062 - loss: 1.8854 - top-5-accuracy: 0.8438

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 550ms/step - accuracy: 0.4453 - loss: 1.7532 - top-5-accuracy: 0.8672

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  14s 534ms/step - accuracy: 0.4601 - loss: 1.6861 - top-5-accuracy: 0.8802

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 539ms/step - accuracy: 0.4779 - loss: 1.6240 - top-5-accuracy: 0.8906

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 541ms/step - accuracy: 0.4748 - loss: 1.6059 - top-5-accuracy: 0.8938

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.4738 - loss: 1.5912 - top-5-accuracy: 0.8967

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 552ms/step - accuracy: 0.4737 - loss: 1.5767 - top-5-accuracy: 0.9000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 550ms/step - accuracy: 0.4741 - loss: 1.5635 - top-5-accuracy: 0.9027

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 549ms/step - accuracy: 0.4754 - loss: 1.5512 - top-5-accuracy: 0.9058

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 548ms/step - accuracy: 0.4757 - loss: 1.5416 - top-5-accuracy: 0.9087

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 552ms/step - accuracy: 0.4750 - loss: 1.5354 - top-5-accuracy: 0.9103

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 552ms/step - accuracy: 0.4741 - loss: 1.5305 - top-5-accuracy: 0.9112

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 556ms/step - accuracy: 0.4733 - loss: 1.5262 - top-5-accuracy: 0.9119

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 556ms/step - accuracy: 0.4728 - loss: 1.5221 - top-5-accuracy: 0.9130 

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 556ms/step - accuracy: 0.4724 - loss: 1.5189 - top-5-accuracy: 0.9139

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 557ms/step - accuracy: 0.4716 - loss: 1.5175 - top-5-accuracy: 0.9144

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 557ms/step - accuracy: 0.4704 - loss: 1.5169 - top-5-accuracy: 0.9150

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 560ms/step - accuracy: 0.4694 - loss: 1.5164 - top-5-accuracy: 0.9151

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 557ms/step - accuracy: 0.4683 - loss: 1.5161 - top-5-accuracy: 0.9152

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 557ms/step - accuracy: 0.4676 - loss: 1.5154 - top-5-accuracy: 0.9153

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 557ms/step - accuracy: 0.4668 - loss: 1.5150 - top-5-accuracy: 0.9153

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 556ms/step - accuracy: 0.4659 - loss: 1.5155 - top-5-accuracy: 0.9152

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 555ms/step - accuracy: 0.4654 - loss: 1.5158 - top-5-accuracy: 0.9152

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 555ms/step - accuracy: 0.4648 - loss: 1.5161 - top-5-accuracy: 0.9153

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 555ms/step - accuracy: 0.4644 - loss: 1.5162 - top-5-accuracy: 0.9154

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 554ms/step - accuracy: 0.4642 - loss: 1.5161 - top-5-accuracy: 0.9156

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 554ms/step - accuracy: 0.4640 - loss: 1.5161 - top-5-accuracy: 0.9156

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 554ms/step - accuracy: 0.4638 - loss: 1.5162 - top-5-accuracy: 0.9156

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 554ms/step - accuracy: 0.4638 - loss: 1.5159 - top-5-accuracy: 0.9157

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 553ms/step - accuracy: 0.4639 - loss: 1.5155 - top-5-accuracy: 0.9158

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 543ms/step - accuracy: 0.4640 - loss: 1.5147 - top-5-accuracy: 0.9159

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 586ms/step - accuracy: 0.4642 - loss: 1.5140 - top-5-accuracy: 0.9161 - val_accuracy: 0.5404 - val_loss: 1.4683 - val_top-5-accuracy: 0.9130


<div class="k-default-codeblock">
```
Epoch 19/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 568ms/step - accuracy: 0.5312 - loss: 1.5865 - top-5-accuracy: 0.7812

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  16s 555ms/step - accuracy: 0.5312 - loss: 1.5392 - top-5-accuracy: 0.8047

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 541ms/step - accuracy: 0.5347 - loss: 1.5445 - top-5-accuracy: 0.8212

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.5241 - loss: 1.5477 - top-5-accuracy: 0.8327

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.5093 - loss: 1.5554 - top-5-accuracy: 0.8399

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.4973 - loss: 1.5541 - top-5-accuracy: 0.8466

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.4900 - loss: 1.5477 - top-5-accuracy: 0.8532

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 552ms/step - accuracy: 0.4859 - loss: 1.5405 - top-5-accuracy: 0.8589

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 552ms/step - accuracy: 0.4809 - loss: 1.5379 - top-5-accuracy: 0.8630

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 552ms/step - accuracy: 0.4766 - loss: 1.5344 - top-5-accuracy: 0.8670

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 552ms/step - accuracy: 0.4730 - loss: 1.5317 - top-5-accuracy: 0.8703

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 551ms/step - accuracy: 0.4709 - loss: 1.5278 - top-5-accuracy: 0.8735

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 551ms/step - accuracy: 0.4700 - loss: 1.5238 - top-5-accuracy: 0.8762 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 551ms/step - accuracy: 0.4696 - loss: 1.5200 - top-5-accuracy: 0.8788

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 551ms/step - accuracy: 0.4694 - loss: 1.5163 - top-5-accuracy: 0.8814

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 550ms/step - accuracy: 0.4690 - loss: 1.5131 - top-5-accuracy: 0.8835

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 550ms/step - accuracy: 0.4683 - loss: 1.5108 - top-5-accuracy: 0.8856

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 550ms/step - accuracy: 0.4676 - loss: 1.5087 - top-5-accuracy: 0.8875

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 550ms/step - accuracy: 0.4668 - loss: 1.5073 - top-5-accuracy: 0.8892

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 549ms/step - accuracy: 0.4664 - loss: 1.5053 - top-5-accuracy: 0.8907

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 550ms/step - accuracy: 0.4662 - loss: 1.5032 - top-5-accuracy: 0.8921

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 551ms/step - accuracy: 0.4661 - loss: 1.5016 - top-5-accuracy: 0.8936

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 551ms/step - accuracy: 0.4660 - loss: 1.4998 - top-5-accuracy: 0.8949

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 551ms/step - accuracy: 0.4659 - loss: 1.4982 - top-5-accuracy: 0.8962

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 551ms/step - accuracy: 0.4657 - loss: 1.4967 - top-5-accuracy: 0.8973

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 551ms/step - accuracy: 0.4655 - loss: 1.4958 - top-5-accuracy: 0.8983

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 551ms/step - accuracy: 0.4651 - loss: 1.4950 - top-5-accuracy: 0.8992

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 550ms/step - accuracy: 0.4648 - loss: 1.4943 - top-5-accuracy: 0.9001

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 551ms/step - accuracy: 0.4646 - loss: 1.4935 - top-5-accuracy: 0.9009

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 551ms/step - accuracy: 0.4644 - loss: 1.4924 - top-5-accuracy: 0.9017

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 540ms/step - accuracy: 0.4642 - loss: 1.4912 - top-5-accuracy: 0.9025

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 583ms/step - accuracy: 0.4641 - loss: 1.4900 - top-5-accuracy: 0.9032 - val_accuracy: 0.4472 - val_loss: 1.5089 - val_top-5-accuracy: 0.9006


<div class="k-default-codeblock">
```
Epoch 20/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 558ms/step - accuracy: 0.5000 - loss: 1.8358 - top-5-accuracy: 0.8125

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.5156 - loss: 1.7426 - top-5-accuracy: 0.8203

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 548ms/step - accuracy: 0.5069 - loss: 1.7526 - top-5-accuracy: 0.8108

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 551ms/step - accuracy: 0.5052 - loss: 1.7318 - top-5-accuracy: 0.8092

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 552ms/step - accuracy: 0.5079 - loss: 1.7071 - top-5-accuracy: 0.8124

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 552ms/step - accuracy: 0.5066 - loss: 1.6845 - top-5-accuracy: 0.8194

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 550ms/step - accuracy: 0.5050 - loss: 1.6659 - top-5-accuracy: 0.8273

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 550ms/step - accuracy: 0.5063 - loss: 1.6468 - top-5-accuracy: 0.8347

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 549ms/step - accuracy: 0.5056 - loss: 1.6332 - top-5-accuracy: 0.8408

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 549ms/step - accuracy: 0.5041 - loss: 1.6248 - top-5-accuracy: 0.8439

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 549ms/step - accuracy: 0.5030 - loss: 1.6187 - top-5-accuracy: 0.8459

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.5021 - loss: 1.6126 - top-5-accuracy: 0.8481

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 547ms/step - accuracy: 0.5025 - loss: 1.6051 - top-5-accuracy: 0.8507 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 547ms/step - accuracy: 0.5026 - loss: 1.5988 - top-5-accuracy: 0.8531

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 547ms/step - accuracy: 0.5030 - loss: 1.5926 - top-5-accuracy: 0.8554

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 547ms/step - accuracy: 0.5038 - loss: 1.5862 - top-5-accuracy: 0.8577

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.5045 - loss: 1.5801 - top-5-accuracy: 0.8600

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.5051 - loss: 1.5745 - top-5-accuracy: 0.8622

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5048 - loss: 1.5700 - top-5-accuracy: 0.8641

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 550ms/step - accuracy: 0.5046 - loss: 1.5656 - top-5-accuracy: 0.8660

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 550ms/step - accuracy: 0.5041 - loss: 1.5617 - top-5-accuracy: 0.8678

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 549ms/step - accuracy: 0.5034 - loss: 1.5581 - top-5-accuracy: 0.8695

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 550ms/step - accuracy: 0.5027 - loss: 1.5550 - top-5-accuracy: 0.8712

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 550ms/step - accuracy: 0.5020 - loss: 1.5520 - top-5-accuracy: 0.8730

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 549ms/step - accuracy: 0.5012 - loss: 1.5492 - top-5-accuracy: 0.8746

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 549ms/step - accuracy: 0.5002 - loss: 1.5470 - top-5-accuracy: 0.8761

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 549ms/step - accuracy: 0.4994 - loss: 1.5445 - top-5-accuracy: 0.8775

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 549ms/step - accuracy: 0.4987 - loss: 1.5421 - top-5-accuracy: 0.8788

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 549ms/step - accuracy: 0.4981 - loss: 1.5396 - top-5-accuracy: 0.8802

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 549ms/step - accuracy: 0.4976 - loss: 1.5371 - top-5-accuracy: 0.8814

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 538ms/step - accuracy: 0.4972 - loss: 1.5349 - top-5-accuracy: 0.8826

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 581ms/step - accuracy: 0.4967 - loss: 1.5328 - top-5-accuracy: 0.8836 - val_accuracy: 0.5031 - val_loss: 1.3945 - val_top-5-accuracy: 0.8882


<div class="k-default-codeblock">
```
Epoch 21/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 558ms/step - accuracy: 0.6250 - loss: 1.3983 - top-5-accuracy: 0.8125

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.5781 - loss: 1.5331 - top-5-accuracy: 0.7969

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.5660 - loss: 1.5379 - top-5-accuracy: 0.8090

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.5573 - loss: 1.5214 - top-5-accuracy: 0.8177

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.5521 - loss: 1.5107 - top-5-accuracy: 0.8242

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.5443 - loss: 1.5056 - top-5-accuracy: 0.8309

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.5392 - loss: 1.4960 - top-5-accuracy: 0.8378

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.5363 - loss: 1.4869 - top-5-accuracy: 0.8435

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.5315 - loss: 1.4821 - top-5-accuracy: 0.8485

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.5274 - loss: 1.4813 - top-5-accuracy: 0.8515

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.5246 - loss: 1.4793 - top-5-accuracy: 0.8546

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.5232 - loss: 1.4762 - top-5-accuracy: 0.8576

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.5226 - loss: 1.4723 - top-5-accuracy: 0.8606 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.5216 - loss: 1.4697 - top-5-accuracy: 0.8636

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.5210 - loss: 1.4665 - top-5-accuracy: 0.8664

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.5204 - loss: 1.4634 - top-5-accuracy: 0.8687

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.5200 - loss: 1.4600 - top-5-accuracy: 0.8708

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.5192 - loss: 1.4572 - top-5-accuracy: 0.8728

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5185 - loss: 1.4548 - top-5-accuracy: 0.8747

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5179 - loss: 1.4521 - top-5-accuracy: 0.8766

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.5172 - loss: 1.4495 - top-5-accuracy: 0.8783

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5165 - loss: 1.4473 - top-5-accuracy: 0.8801

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.5159 - loss: 1.4448 - top-5-accuracy: 0.8817

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.5152 - loss: 1.4428 - top-5-accuracy: 0.8834

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.5144 - loss: 1.4412 - top-5-accuracy: 0.8849

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.5137 - loss: 1.4394 - top-5-accuracy: 0.8864

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.5129 - loss: 1.4378 - top-5-accuracy: 0.8878

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.5122 - loss: 1.4363 - top-5-accuracy: 0.8892

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.5116 - loss: 1.4344 - top-5-accuracy: 0.8906

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.5111 - loss: 1.4324 - top-5-accuracy: 0.8919

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.5106 - loss: 1.4304 - top-5-accuracy: 0.8932

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 579ms/step - accuracy: 0.5102 - loss: 1.4284 - top-5-accuracy: 0.8944 - val_accuracy: 0.5590 - val_loss: 1.2147 - val_top-5-accuracy: 0.9130


<div class="k-default-codeblock">
```
Epoch 22/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 560ms/step - accuracy: 0.5625 - loss: 1.5127 - top-5-accuracy: 0.9062

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.5781 - loss: 1.4595 - top-5-accuracy: 0.9141

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.5799 - loss: 1.4045 - top-5-accuracy: 0.9184

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.5697 - loss: 1.3875 - top-5-accuracy: 0.9212

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.5582 - loss: 1.3873 - top-5-accuracy: 0.9220

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.5503 - loss: 1.3865 - top-5-accuracy: 0.9228

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.5469 - loss: 1.3820 - top-5-accuracy: 0.9237

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.5415 - loss: 1.3815 - top-5-accuracy: 0.9249

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.5385 - loss: 1.3798 - top-5-accuracy: 0.9263

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.5365 - loss: 1.3772 - top-5-accuracy: 0.9277

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.5347 - loss: 1.3762 - top-5-accuracy: 0.9284

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.5329 - loss: 1.3754 - top-5-accuracy: 0.9289

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 544ms/step - accuracy: 0.5328 - loss: 1.3732 - top-5-accuracy: 0.9296 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 544ms/step - accuracy: 0.5320 - loss: 1.3710 - top-5-accuracy: 0.9303

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.5317 - loss: 1.3692 - top-5-accuracy: 0.9306

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.5313 - loss: 1.3681 - top-5-accuracy: 0.9309

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.5306 - loss: 1.3683 - top-5-accuracy: 0.9310

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.5301 - loss: 1.3680 - top-5-accuracy: 0.9312

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.5301 - loss: 1.3673 - top-5-accuracy: 0.9315

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5300 - loss: 1.3667 - top-5-accuracy: 0.9319

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.5297 - loss: 1.3664 - top-5-accuracy: 0.9322

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5294 - loss: 1.3661 - top-5-accuracy: 0.9325

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5290 - loss: 1.3660 - top-5-accuracy: 0.9329

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.5286 - loss: 1.3657 - top-5-accuracy: 0.9333

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.5283 - loss: 1.3653 - top-5-accuracy: 0.9337

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 546ms/step - accuracy: 0.5280 - loss: 1.3651 - top-5-accuracy: 0.9342

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.5277 - loss: 1.3649 - top-5-accuracy: 0.9346

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.5273 - loss: 1.3647 - top-5-accuracy: 0.9351

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.5269 - loss: 1.3646 - top-5-accuracy: 0.9355

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.5267 - loss: 1.3643 - top-5-accuracy: 0.9359

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.5266 - loss: 1.3635 - top-5-accuracy: 0.9364

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.5265 - loss: 1.3627 - top-5-accuracy: 0.9368 - val_accuracy: 0.5963 - val_loss: 1.1398 - val_top-5-accuracy: 0.9317


<div class="k-default-codeblock">
```
Epoch 23/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  1:35 3s/step - accuracy: 0.5625 - loss: 1.6931 - top-5-accuracy: 0.8125

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 617ms/step - accuracy: 0.6016 - loss: 1.5023 - top-5-accuracy: 0.8359

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 615ms/step - accuracy: 0.6163 - loss: 1.4456 - top-5-accuracy: 0.8490

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  16s 610ms/step - accuracy: 0.6204 - loss: 1.4090 - top-5-accuracy: 0.8574

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  15s 594ms/step - accuracy: 0.6151 - loss: 1.3939 - top-5-accuracy: 0.8634

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 585ms/step - accuracy: 0.6037 - loss: 1.3834 - top-5-accuracy: 0.8697

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 579ms/step - accuracy: 0.5978 - loss: 1.3711 - top-5-accuracy: 0.8756

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  13s 574ms/step - accuracy: 0.5939 - loss: 1.3596 - top-5-accuracy: 0.8814

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 572ms/step - accuracy: 0.5897 - loss: 1.3506 - top-5-accuracy: 0.8864

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 569ms/step - accuracy: 0.5860 - loss: 1.3433 - top-5-accuracy: 0.8912

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 567ms/step - accuracy: 0.5823 - loss: 1.3383 - top-5-accuracy: 0.8949

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 565ms/step - accuracy: 0.5800 - loss: 1.3323 - top-5-accuracy: 0.8985

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 564ms/step - accuracy: 0.5777 - loss: 1.3273 - top-5-accuracy: 0.9013

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 562ms/step - accuracy: 0.5767 - loss: 1.3220 - top-5-accuracy: 0.9037 

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 561ms/step - accuracy: 0.5753 - loss: 1.3178 - top-5-accuracy: 0.9058

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 560ms/step - accuracy: 0.5735 - loss: 1.3145 - top-5-accuracy: 0.9078

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 559ms/step - accuracy: 0.5717 - loss: 1.3116 - top-5-accuracy: 0.9097

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 558ms/step - accuracy: 0.5701 - loss: 1.3083 - top-5-accuracy: 0.9115

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 557ms/step - accuracy: 0.5687 - loss: 1.3056 - top-5-accuracy: 0.9131

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 557ms/step - accuracy: 0.5676 - loss: 1.3025 - top-5-accuracy: 0.9147

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 556ms/step - accuracy: 0.5662 - loss: 1.3003 - top-5-accuracy: 0.9162

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 555ms/step - accuracy: 0.5649 - loss: 1.2983 - top-5-accuracy: 0.9176

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 555ms/step - accuracy: 0.5639 - loss: 1.2962 - top-5-accuracy: 0.9189

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 554ms/step - accuracy: 0.5629 - loss: 1.2948 - top-5-accuracy: 0.9201

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 554ms/step - accuracy: 0.5620 - loss: 1.2933 - top-5-accuracy: 0.9213

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 554ms/step - accuracy: 0.5613 - loss: 1.2917 - top-5-accuracy: 0.9225

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 553ms/step - accuracy: 0.5606 - loss: 1.2901 - top-5-accuracy: 0.9236

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 553ms/step - accuracy: 0.5600 - loss: 1.2885 - top-5-accuracy: 0.9247

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 553ms/step - accuracy: 0.5595 - loss: 1.2868 - top-5-accuracy: 0.9258

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 552ms/step - accuracy: 0.5591 - loss: 1.2851 - top-5-accuracy: 0.9268

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 542ms/step - accuracy: 0.5588 - loss: 1.2831 - top-5-accuracy: 0.9277

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 21s 585ms/step - accuracy: 0.5585 - loss: 1.2811 - top-5-accuracy: 0.9286 - val_accuracy: 0.5093 - val_loss: 1.3104 - val_top-5-accuracy: 0.9441


<div class="k-default-codeblock">
```
Epoch 24/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 564ms/step - accuracy: 0.5000 - loss: 1.8099 - top-5-accuracy: 0.8125

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.5391 - loss: 1.6169 - top-5-accuracy: 0.8438

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 550ms/step - accuracy: 0.5399 - loss: 1.5388 - top-5-accuracy: 0.8611

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 551ms/step - accuracy: 0.5456 - loss: 1.4892 - top-5-accuracy: 0.8704

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 550ms/step - accuracy: 0.5427 - loss: 1.4612 - top-5-accuracy: 0.8801

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 548ms/step - accuracy: 0.5399 - loss: 1.4408 - top-5-accuracy: 0.8879

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 548ms/step - accuracy: 0.5381 - loss: 1.4284 - top-5-accuracy: 0.8925

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 548ms/step - accuracy: 0.5377 - loss: 1.4173 - top-5-accuracy: 0.8961

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 549ms/step - accuracy: 0.5374 - loss: 1.4061 - top-5-accuracy: 0.8996

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 548ms/step - accuracy: 0.5380 - loss: 1.3933 - top-5-accuracy: 0.9031

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.5382 - loss: 1.3851 - top-5-accuracy: 0.9057

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.5382 - loss: 1.3777 - top-5-accuracy: 0.9083

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 548ms/step - accuracy: 0.5383 - loss: 1.3711 - top-5-accuracy: 0.9108 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 548ms/step - accuracy: 0.5384 - loss: 1.3653 - top-5-accuracy: 0.9128

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 548ms/step - accuracy: 0.5390 - loss: 1.3595 - top-5-accuracy: 0.9146

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 547ms/step - accuracy: 0.5390 - loss: 1.3552 - top-5-accuracy: 0.9162

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 547ms/step - accuracy: 0.5388 - loss: 1.3519 - top-5-accuracy: 0.9176

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 547ms/step - accuracy: 0.5380 - loss: 1.3487 - top-5-accuracy: 0.9191

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.5375 - loss: 1.3455 - top-5-accuracy: 0.9204

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.5368 - loss: 1.3430 - top-5-accuracy: 0.9215

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 547ms/step - accuracy: 0.5360 - loss: 1.3406 - top-5-accuracy: 0.9226

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.5353 - loss: 1.3384 - top-5-accuracy: 0.9236

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.5341 - loss: 1.3376 - top-5-accuracy: 0.9245

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 547ms/step - accuracy: 0.5332 - loss: 1.3365 - top-5-accuracy: 0.9254

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 547ms/step - accuracy: 0.5322 - loss: 1.3358 - top-5-accuracy: 0.9263

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 547ms/step - accuracy: 0.5315 - loss: 1.3347 - top-5-accuracy: 0.9272

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 547ms/step - accuracy: 0.5312 - loss: 1.3330 - top-5-accuracy: 0.9281

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 548ms/step - accuracy: 0.5310 - loss: 1.3316 - top-5-accuracy: 0.9290

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 548ms/step - accuracy: 0.5306 - loss: 1.3303 - top-5-accuracy: 0.9299

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 548ms/step - accuracy: 0.5304 - loss: 1.3289 - top-5-accuracy: 0.9307

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 537ms/step - accuracy: 0.5303 - loss: 1.3274 - top-5-accuracy: 0.9316

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 580ms/step - accuracy: 0.5301 - loss: 1.3259 - top-5-accuracy: 0.9324 - val_accuracy: 0.5528 - val_loss: 1.2361 - val_top-5-accuracy: 0.9441


<div class="k-default-codeblock">
```
Epoch 25/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  18s 627ms/step - accuracy: 0.6250 - loss: 1.3738 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 611ms/step - accuracy: 0.6250 - loss: 1.2785 - top-5-accuracy: 0.9531

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  16s 583ms/step - accuracy: 0.6181 - loss: 1.2486 - top-5-accuracy: 0.9583

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  15s 572ms/step - accuracy: 0.5924 - loss: 1.2713 - top-5-accuracy: 0.9590

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 566ms/step - accuracy: 0.5790 - loss: 1.2807 - top-5-accuracy: 0.9609

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 563ms/step - accuracy: 0.5693 - loss: 1.2846 - top-5-accuracy: 0.9614

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 560ms/step - accuracy: 0.5626 - loss: 1.2885 - top-5-accuracy: 0.9605

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 557ms/step - accuracy: 0.5562 - loss: 1.2988 - top-5-accuracy: 0.9571

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 556ms/step - accuracy: 0.5515 - loss: 1.3050 - top-5-accuracy: 0.9550

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 555ms/step - accuracy: 0.5485 - loss: 1.3095 - top-5-accuracy: 0.9529

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 554ms/step - accuracy: 0.5462 - loss: 1.3119 - top-5-accuracy: 0.9515

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 553ms/step - accuracy: 0.5447 - loss: 1.3116 - top-5-accuracy: 0.9508

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 553ms/step - accuracy: 0.5437 - loss: 1.3115 - top-5-accuracy: 0.9499 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 552ms/step - accuracy: 0.5431 - loss: 1.3104 - top-5-accuracy: 0.9494

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 552ms/step - accuracy: 0.5430 - loss: 1.3083 - top-5-accuracy: 0.9490

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 551ms/step - accuracy: 0.5422 - loss: 1.3075 - top-5-accuracy: 0.9486

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 551ms/step - accuracy: 0.5409 - loss: 1.3074 - top-5-accuracy: 0.9484

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 550ms/step - accuracy: 0.5398 - loss: 1.3068 - top-5-accuracy: 0.9484

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 550ms/step - accuracy: 0.5392 - loss: 1.3054 - top-5-accuracy: 0.9485

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 550ms/step - accuracy: 0.5385 - loss: 1.3041 - top-5-accuracy: 0.9485

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 550ms/step - accuracy: 0.5376 - loss: 1.3031 - top-5-accuracy: 0.9485

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 550ms/step - accuracy: 0.5367 - loss: 1.3021 - top-5-accuracy: 0.9487

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 550ms/step - accuracy: 0.5359 - loss: 1.3009 - top-5-accuracy: 0.9489

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 550ms/step - accuracy: 0.5353 - loss: 1.3002 - top-5-accuracy: 0.9490

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 550ms/step - accuracy: 0.5348 - loss: 1.2993 - top-5-accuracy: 0.9491

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 550ms/step - accuracy: 0.5344 - loss: 1.2984 - top-5-accuracy: 0.9493

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 550ms/step - accuracy: 0.5341 - loss: 1.2973 - top-5-accuracy: 0.9495

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 549ms/step - accuracy: 0.5336 - loss: 1.2966 - top-5-accuracy: 0.9497

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 549ms/step - accuracy: 0.5334 - loss: 1.2956 - top-5-accuracy: 0.9500

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 549ms/step - accuracy: 0.5332 - loss: 1.2943 - top-5-accuracy: 0.9503

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 538ms/step - accuracy: 0.5332 - loss: 1.2925 - top-5-accuracy: 0.9505

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 581ms/step - accuracy: 0.5332 - loss: 1.2909 - top-5-accuracy: 0.9508 - val_accuracy: 0.6211 - val_loss: 1.0590 - val_top-5-accuracy: 0.9565


<div class="k-default-codeblock">
```
Epoch 26/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 553ms/step - accuracy: 0.6250 - loss: 1.2088 - top-5-accuracy: 0.9688

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.5938 - loss: 1.2395 - top-5-accuracy: 0.9609

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.5938 - loss: 1.2066 - top-5-accuracy: 0.9635

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 548ms/step - accuracy: 0.5879 - loss: 1.1919 - top-5-accuracy: 0.9629

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 550ms/step - accuracy: 0.5866 - loss: 1.1812 - top-5-accuracy: 0.9616

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 548ms/step - accuracy: 0.5886 - loss: 1.1688 - top-5-accuracy: 0.9619

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 549ms/step - accuracy: 0.5925 - loss: 1.1568 - top-5-accuracy: 0.9629

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 549ms/step - accuracy: 0.5966 - loss: 1.1467 - top-5-accuracy: 0.9636

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 548ms/step - accuracy: 0.5982 - loss: 1.1404 - top-5-accuracy: 0.9642

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 548ms/step - accuracy: 0.5993 - loss: 1.1357 - top-5-accuracy: 0.9649

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.6006 - loss: 1.1321 - top-5-accuracy: 0.9658

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.6029 - loss: 1.1270 - top-5-accuracy: 0.9667

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 548ms/step - accuracy: 0.6046 - loss: 1.1238 - top-5-accuracy: 0.9674 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 548ms/step - accuracy: 0.6064 - loss: 1.1212 - top-5-accuracy: 0.9677

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 548ms/step - accuracy: 0.6072 - loss: 1.1193 - top-5-accuracy: 0.9680

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 548ms/step - accuracy: 0.6081 - loss: 1.1178 - top-5-accuracy: 0.9682

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 548ms/step - accuracy: 0.6086 - loss: 1.1168 - top-5-accuracy: 0.9683

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 548ms/step - accuracy: 0.6093 - loss: 1.1156 - top-5-accuracy: 0.9685

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 548ms/step - accuracy: 0.6092 - loss: 1.1161 - top-5-accuracy: 0.9686

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.6091 - loss: 1.1160 - top-5-accuracy: 0.9688

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 547ms/step - accuracy: 0.6088 - loss: 1.1162 - top-5-accuracy: 0.9690

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.6085 - loss: 1.1168 - top-5-accuracy: 0.9692

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.6079 - loss: 1.1178 - top-5-accuracy: 0.9694

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 547ms/step - accuracy: 0.6072 - loss: 1.1188 - top-5-accuracy: 0.9696

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 547ms/step - accuracy: 0.6065 - loss: 1.1197 - top-5-accuracy: 0.9698

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 547ms/step - accuracy: 0.6059 - loss: 1.1204 - top-5-accuracy: 0.9700

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 547ms/step - accuracy: 0.6055 - loss: 1.1209 - top-5-accuracy: 0.9701

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.6050 - loss: 1.1217 - top-5-accuracy: 0.9703

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.6046 - loss: 1.1223 - top-5-accuracy: 0.9705

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.6043 - loss: 1.1225 - top-5-accuracy: 0.9707

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.6040 - loss: 1.1226 - top-5-accuracy: 0.9709

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 579ms/step - accuracy: 0.6038 - loss: 1.1228 - top-5-accuracy: 0.9711 - val_accuracy: 0.5466 - val_loss: 1.1721 - val_top-5-accuracy: 0.9565


<div class="k-default-codeblock">
```
Epoch 27/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 569ms/step - accuracy: 0.5625 - loss: 1.5866 - top-5-accuracy: 0.8438

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 543ms/step - accuracy: 0.5547 - loss: 1.5228 - top-5-accuracy: 0.8438

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.5503 - loss: 1.4975 - top-5-accuracy: 0.8472

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.5553 - loss: 1.4688 - top-5-accuracy: 0.8561

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.5555 - loss: 1.4418 - top-5-accuracy: 0.8661

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.5558 - loss: 1.4225 - top-5-accuracy: 0.8746

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.5536 - loss: 1.4113 - top-5-accuracy: 0.8810

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.5493 - loss: 1.4050 - top-5-accuracy: 0.8861

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.5462 - loss: 1.3989 - top-5-accuracy: 0.8907

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.5450 - loss: 1.3902 - top-5-accuracy: 0.8950

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.5440 - loss: 1.3832 - top-5-accuracy: 0.8984

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.5440 - loss: 1.3751 - top-5-accuracy: 0.9016

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.5447 - loss: 1.3671 - top-5-accuracy: 0.9044 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.5453 - loss: 1.3598 - top-5-accuracy: 0.9068

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.5459 - loss: 1.3533 - top-5-accuracy: 0.9090

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.5457 - loss: 1.3483 - top-5-accuracy: 0.9109

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.5450 - loss: 1.3452 - top-5-accuracy: 0.9124

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.5445 - loss: 1.3418 - top-5-accuracy: 0.9138

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5441 - loss: 1.3382 - top-5-accuracy: 0.9152

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5436 - loss: 1.3347 - top-5-accuracy: 0.9166

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.5434 - loss: 1.3313 - top-5-accuracy: 0.9179

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5434 - loss: 1.3281 - top-5-accuracy: 0.9191

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5436 - loss: 1.3249 - top-5-accuracy: 0.9203

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.5439 - loss: 1.3220 - top-5-accuracy: 0.9214

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.5443 - loss: 1.3188 - top-5-accuracy: 0.9226

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 546ms/step - accuracy: 0.5445 - loss: 1.3159 - top-5-accuracy: 0.9236

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.5449 - loss: 1.3130 - top-5-accuracy: 0.9247

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.5455 - loss: 1.3099 - top-5-accuracy: 0.9257

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.5462 - loss: 1.3066 - top-5-accuracy: 0.9267

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.5469 - loss: 1.3036 - top-5-accuracy: 0.9277

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.5475 - loss: 1.3002 - top-5-accuracy: 0.9286

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 579ms/step - accuracy: 0.5480 - loss: 1.2971 - top-5-accuracy: 0.9295 - val_accuracy: 0.6211 - val_loss: 1.2251 - val_top-5-accuracy: 0.9503


<div class="k-default-codeblock">
```
Epoch 28/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 571ms/step - accuracy: 0.4688 - loss: 1.4967 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 468ms/step - accuracy: 0.5156 - loss: 1.3979 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 467ms/step - accuracy: 0.5347 - loss: 1.3431 - top-5-accuracy: 0.9410

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  12s 468ms/step - accuracy: 0.5475 - loss: 1.3193 - top-5-accuracy: 0.9401

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  12s 471ms/step - accuracy: 0.5543 - loss: 1.2969 - top-5-accuracy: 0.9421

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  11s 471ms/step - accuracy: 0.5591 - loss: 1.2791 - top-5-accuracy: 0.9431

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  11s 474ms/step - accuracy: 0.5634 - loss: 1.2650 - top-5-accuracy: 0.9448

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 473ms/step - accuracy: 0.5687 - loss: 1.2500 - top-5-accuracy: 0.9463

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  10s 472ms/step - accuracy: 0.5734 - loss: 1.2371 - top-5-accuracy: 0.9481

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  9s 472ms/step - accuracy: 0.5770 - loss: 1.2265 - top-5-accuracy: 0.9498 

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  9s 472ms/step - accuracy: 0.5806 - loss: 1.2170 - top-5-accuracy: 0.9513

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  8s 472ms/step - accuracy: 0.5819 - loss: 1.2131 - top-5-accuracy: 0.9516

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  8s 473ms/step - accuracy: 0.5839 - loss: 1.2074 - top-5-accuracy: 0.9522

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 476ms/step - accuracy: 0.5857 - loss: 1.2018 - top-5-accuracy: 0.9528

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  7s 480ms/step - accuracy: 0.5871 - loss: 1.1970 - top-5-accuracy: 0.9533

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 480ms/step - accuracy: 0.5881 - loss: 1.1930 - top-5-accuracy: 0.9538

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  6s 480ms/step - accuracy: 0.5884 - loss: 1.1903 - top-5-accuracy: 0.9541

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  6s 479ms/step - accuracy: 0.5886 - loss: 1.1879 - top-5-accuracy: 0.9544

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 478ms/step - accuracy: 0.5887 - loss: 1.1864 - top-5-accuracy: 0.9547

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 478ms/step - accuracy: 0.5883 - loss: 1.1856 - top-5-accuracy: 0.9548

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  4s 477ms/step - accuracy: 0.5880 - loss: 1.1849 - top-5-accuracy: 0.9550

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 477ms/step - accuracy: 0.5875 - loss: 1.1844 - top-5-accuracy: 0.9552

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  3s 477ms/step - accuracy: 0.5870 - loss: 1.1841 - top-5-accuracy: 0.9553

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 477ms/step - accuracy: 0.5868 - loss: 1.1836 - top-5-accuracy: 0.9556

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 477ms/step - accuracy: 0.5866 - loss: 1.1831 - top-5-accuracy: 0.9557

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 477ms/step - accuracy: 0.5865 - loss: 1.1823 - top-5-accuracy: 0.9559

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  1s 477ms/step - accuracy: 0.5863 - loss: 1.1817 - top-5-accuracy: 0.9561

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 477ms/step - accuracy: 0.5861 - loss: 1.1810 - top-5-accuracy: 0.9563

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  0s 476ms/step - accuracy: 0.5860 - loss: 1.1801 - top-5-accuracy: 0.9565

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 476ms/step - accuracy: 0.5857 - loss: 1.1794 - top-5-accuracy: 0.9567

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 467ms/step - accuracy: 0.5856 - loss: 1.1780 - top-5-accuracy: 0.9569

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 16s 508ms/step - accuracy: 0.5854 - loss: 1.1767 - top-5-accuracy: 0.9571 - val_accuracy: 0.6211 - val_loss: 1.0370 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 29/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 571ms/step - accuracy: 0.6875 - loss: 1.2329 - top-5-accuracy: 0.9062

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  14s 513ms/step - accuracy: 0.6719 - loss: 1.1802 - top-5-accuracy: 0.9219

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  13s 493ms/step - accuracy: 0.6736 - loss: 1.1234 - top-5-accuracy: 0.9340

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  13s 500ms/step - accuracy: 0.6634 - loss: 1.1059 - top-5-accuracy: 0.9408

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 512ms/step - accuracy: 0.6595 - loss: 1.0869 - top-5-accuracy: 0.9451

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  12s 518ms/step - accuracy: 0.6598 - loss: 1.0701 - top-5-accuracy: 0.9490

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  12s 521ms/step - accuracy: 0.6580 - loss: 1.0602 - top-5-accuracy: 0.9519

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 525ms/step - accuracy: 0.6549 - loss: 1.0567 - top-5-accuracy: 0.9530

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 527ms/step - accuracy: 0.6523 - loss: 1.0540 - top-5-accuracy: 0.9540

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 529ms/step - accuracy: 0.6505 - loss: 1.0515 - top-5-accuracy: 0.9551

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 531ms/step - accuracy: 0.6492 - loss: 1.0487 - top-5-accuracy: 0.9564

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 533ms/step - accuracy: 0.6483 - loss: 1.0473 - top-5-accuracy: 0.9572

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 534ms/step - accuracy: 0.6478 - loss: 1.0455 - top-5-accuracy: 0.9581 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 535ms/step - accuracy: 0.6475 - loss: 1.0436 - top-5-accuracy: 0.9588

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 535ms/step - accuracy: 0.6469 - loss: 1.0425 - top-5-accuracy: 0.9594

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 536ms/step - accuracy: 0.6458 - loss: 1.0425 - top-5-accuracy: 0.9598

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 536ms/step - accuracy: 0.6447 - loss: 1.0435 - top-5-accuracy: 0.9601

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  6s 537ms/step - accuracy: 0.6440 - loss: 1.0441 - top-5-accuracy: 0.9605

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 537ms/step - accuracy: 0.6429 - loss: 1.0458 - top-5-accuracy: 0.9607

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 538ms/step - accuracy: 0.6418 - loss: 1.0480 - top-5-accuracy: 0.9608

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 538ms/step - accuracy: 0.6405 - loss: 1.0504 - top-5-accuracy: 0.9608

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 538ms/step - accuracy: 0.6394 - loss: 1.0527 - top-5-accuracy: 0.9608

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 539ms/step - accuracy: 0.6383 - loss: 1.0545 - top-5-accuracy: 0.9608

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 539ms/step - accuracy: 0.6372 - loss: 1.0562 - top-5-accuracy: 0.9609

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 539ms/step - accuracy: 0.6361 - loss: 1.0579 - top-5-accuracy: 0.9611

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 540ms/step - accuracy: 0.6352 - loss: 1.0591 - top-5-accuracy: 0.9612

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 540ms/step - accuracy: 0.6343 - loss: 1.0601 - top-5-accuracy: 0.9614

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 540ms/step - accuracy: 0.6334 - loss: 1.0609 - top-5-accuracy: 0.9616

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 540ms/step - accuracy: 0.6328 - loss: 1.0616 - top-5-accuracy: 0.9618

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 540ms/step - accuracy: 0.6324 - loss: 1.0620 - top-5-accuracy: 0.9620

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 530ms/step - accuracy: 0.6320 - loss: 1.0625 - top-5-accuracy: 0.9622

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 573ms/step - accuracy: 0.6316 - loss: 1.0629 - top-5-accuracy: 0.9624 - val_accuracy: 0.6894 - val_loss: 0.9480 - val_top-5-accuracy: 0.9379


<div class="k-default-codeblock">
```
Epoch 30/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 558ms/step - accuracy: 0.5625 - loss: 1.2550 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.5859 - loss: 1.2342 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.5955 - loss: 1.1869 - top-5-accuracy: 0.9444

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 543ms/step - accuracy: 0.5931 - loss: 1.1619 - top-5-accuracy: 0.9486

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 542ms/step - accuracy: 0.5895 - loss: 1.1518 - top-5-accuracy: 0.9501

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.5867 - loss: 1.1428 - top-5-accuracy: 0.9523

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.5890 - loss: 1.1317 - top-5-accuracy: 0.9540

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.5896 - loss: 1.1255 - top-5-accuracy: 0.9559

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.5897 - loss: 1.1197 - top-5-accuracy: 0.9577

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.5898 - loss: 1.1148 - top-5-accuracy: 0.9594

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.5899 - loss: 1.1120 - top-5-accuracy: 0.9608

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.5911 - loss: 1.1082 - top-5-accuracy: 0.9619

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.5920 - loss: 1.1046 - top-5-accuracy: 0.9626 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 546ms/step - accuracy: 0.5932 - loss: 1.1016 - top-5-accuracy: 0.9634

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 546ms/step - accuracy: 0.5943 - loss: 1.0987 - top-5-accuracy: 0.9641

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.5953 - loss: 1.0963 - top-5-accuracy: 0.9648

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.5965 - loss: 1.0940 - top-5-accuracy: 0.9655

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.5975 - loss: 1.0914 - top-5-accuracy: 0.9661

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5981 - loss: 1.0896 - top-5-accuracy: 0.9668

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.5985 - loss: 1.0877 - top-5-accuracy: 0.9674

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.5989 - loss: 1.0866 - top-5-accuracy: 0.9679

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5994 - loss: 1.0855 - top-5-accuracy: 0.9684

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.5998 - loss: 1.0842 - top-5-accuracy: 0.9689

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.6003 - loss: 1.0829 - top-5-accuracy: 0.9694

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.6010 - loss: 1.0814 - top-5-accuracy: 0.9698

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.6015 - loss: 1.0801 - top-5-accuracy: 0.9703

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.6022 - loss: 1.0785 - top-5-accuracy: 0.9707

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.6027 - loss: 1.0773 - top-5-accuracy: 0.9711

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.6032 - loss: 1.0762 - top-5-accuracy: 0.9715

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.6037 - loss: 1.0751 - top-5-accuracy: 0.9718

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.6042 - loss: 1.0734 - top-5-accuracy: 0.9722

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.6047 - loss: 1.0719 - top-5-accuracy: 0.9725 - val_accuracy: 0.6149 - val_loss: 0.9407 - val_top-5-accuracy: 0.9752


<div class="k-default-codeblock">
```
Epoch 31/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 560ms/step - accuracy: 0.5938 - loss: 0.9510 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.6172 - loss: 0.9659 - top-5-accuracy: 0.9844

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 543ms/step - accuracy: 0.6372 - loss: 0.9590 - top-5-accuracy: 0.9792

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.6341 - loss: 0.9950 - top-5-accuracy: 0.9707

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 548ms/step - accuracy: 0.6285 - loss: 1.0223 - top-5-accuracy: 0.9678

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.6262 - loss: 1.0395 - top-5-accuracy: 0.9671

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.6286 - loss: 1.0442 - top-5-accuracy: 0.9667

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.6306 - loss: 1.0449 - top-5-accuracy: 0.9670

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.6304 - loss: 1.0494 - top-5-accuracy: 0.9675

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 547ms/step - accuracy: 0.6314 - loss: 1.0528 - top-5-accuracy: 0.9680

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.6323 - loss: 1.0540 - top-5-accuracy: 0.9686

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.6341 - loss: 1.0531 - top-5-accuracy: 0.9690

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 547ms/step - accuracy: 0.6351 - loss: 1.0529 - top-5-accuracy: 0.9694 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 546ms/step - accuracy: 0.6363 - loss: 1.0518 - top-5-accuracy: 0.9696

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 546ms/step - accuracy: 0.6372 - loss: 1.0500 - top-5-accuracy: 0.9700

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.6377 - loss: 1.0480 - top-5-accuracy: 0.9704

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 547ms/step - accuracy: 0.6382 - loss: 1.0467 - top-5-accuracy: 0.9706

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.6388 - loss: 1.0454 - top-5-accuracy: 0.9708

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.6395 - loss: 1.0438 - top-5-accuracy: 0.9710

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.6398 - loss: 1.0429 - top-5-accuracy: 0.9711

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.6403 - loss: 1.0421 - top-5-accuracy: 0.9711

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.6404 - loss: 1.0417 - top-5-accuracy: 0.9712

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.6404 - loss: 1.0412 - top-5-accuracy: 0.9713

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.6401 - loss: 1.0411 - top-5-accuracy: 0.9715

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.6398 - loss: 1.0411 - top-5-accuracy: 0.9716

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 546ms/step - accuracy: 0.6394 - loss: 1.0412 - top-5-accuracy: 0.9718

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.6389 - loss: 1.0411 - top-5-accuracy: 0.9719

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.6384 - loss: 1.0410 - top-5-accuracy: 0.9721

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.6378 - loss: 1.0411 - top-5-accuracy: 0.9723

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.6373 - loss: 1.0413 - top-5-accuracy: 0.9724

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.6369 - loss: 1.0410 - top-5-accuracy: 0.9725

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.6365 - loss: 1.0407 - top-5-accuracy: 0.9726 - val_accuracy: 0.5901 - val_loss: 1.0794 - val_top-5-accuracy: 0.9565


<div class="k-default-codeblock">
```
Epoch 32/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 559ms/step - accuracy: 0.5625 - loss: 1.4305 - top-5-accuracy: 0.9062

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  16s 555ms/step - accuracy: 0.5938 - loss: 1.3526 - top-5-accuracy: 0.9062

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 552ms/step - accuracy: 0.6146 - loss: 1.2976 - top-5-accuracy: 0.9097

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 550ms/step - accuracy: 0.6230 - loss: 1.2567 - top-5-accuracy: 0.9167

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 549ms/step - accuracy: 0.6322 - loss: 1.2164 - top-5-accuracy: 0.9233

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 548ms/step - accuracy: 0.6388 - loss: 1.1833 - top-5-accuracy: 0.9292

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 548ms/step - accuracy: 0.6400 - loss: 1.1651 - top-5-accuracy: 0.9335

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.6372 - loss: 1.1574 - top-5-accuracy: 0.9370

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.6374 - loss: 1.1467 - top-5-accuracy: 0.9401

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.6402 - loss: 1.1338 - top-5-accuracy: 0.9430

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.6416 - loss: 1.1242 - top-5-accuracy: 0.9453

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.6433 - loss: 1.1151 - top-5-accuracy: 0.9473

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.6447 - loss: 1.1074 - top-5-accuracy: 0.9491 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 546ms/step - accuracy: 0.6469 - loss: 1.0984 - top-5-accuracy: 0.9508

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 546ms/step - accuracy: 0.6485 - loss: 1.0911 - top-5-accuracy: 0.9522

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.6495 - loss: 1.0850 - top-5-accuracy: 0.9533

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.6503 - loss: 1.0801 - top-5-accuracy: 0.9542

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 547ms/step - accuracy: 0.6507 - loss: 1.0758 - top-5-accuracy: 0.9550

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.6509 - loss: 1.0721 - top-5-accuracy: 0.9558

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 548ms/step - accuracy: 0.6511 - loss: 1.0689 - top-5-accuracy: 0.9563

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 548ms/step - accuracy: 0.6512 - loss: 1.0658 - top-5-accuracy: 0.9569

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 549ms/step - accuracy: 0.6513 - loss: 1.0631 - top-5-accuracy: 0.9575

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 549ms/step - accuracy: 0.6514 - loss: 1.0604 - top-5-accuracy: 0.9580

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 550ms/step - accuracy: 0.6510 - loss: 1.0585 - top-5-accuracy: 0.9585

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 550ms/step - accuracy: 0.6505 - loss: 1.0567 - top-5-accuracy: 0.9590

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 550ms/step - accuracy: 0.6501 - loss: 1.0550 - top-5-accuracy: 0.9595

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 550ms/step - accuracy: 0.6497 - loss: 1.0533 - top-5-accuracy: 0.9600

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 551ms/step - accuracy: 0.6492 - loss: 1.0521 - top-5-accuracy: 0.9604

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 555ms/step - accuracy: 0.6487 - loss: 1.0509 - top-5-accuracy: 0.9608

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 568ms/step - accuracy: 0.6483 - loss: 1.0496 - top-5-accuracy: 0.9613

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 556ms/step - accuracy: 0.6479 - loss: 1.0483 - top-5-accuracy: 0.9617

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 19s 604ms/step - accuracy: 0.6475 - loss: 1.0471 - top-5-accuracy: 0.9621 - val_accuracy: 0.5776 - val_loss: 1.0451 - val_top-5-accuracy: 0.9627


<div class="k-default-codeblock">
```
Epoch 33/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  19s 644ms/step - accuracy: 0.6562 - loss: 0.8805 - top-5-accuracy: 0.9688

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 598ms/step - accuracy: 0.6328 - loss: 0.9730 - top-5-accuracy: 0.9609

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 624ms/step - accuracy: 0.6163 - loss: 1.0163 - top-5-accuracy: 0.9531

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  16s 595ms/step - accuracy: 0.6107 - loss: 1.0487 - top-5-accuracy: 0.9492

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  15s 583ms/step - accuracy: 0.6110 - loss: 1.0552 - top-5-accuracy: 0.9494

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 569ms/step - accuracy: 0.6116 - loss: 1.0569 - top-5-accuracy: 0.9509

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 566ms/step - accuracy: 0.6148 - loss: 1.0524 - top-5-accuracy: 0.9528

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  13s 577ms/step - accuracy: 0.6176 - loss: 1.0464 - top-5-accuracy: 0.9548

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 570ms/step - accuracy: 0.6184 - loss: 1.0422 - top-5-accuracy: 0.9559

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 571ms/step - accuracy: 0.6200 - loss: 1.0386 - top-5-accuracy: 0.9572

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 561ms/step - accuracy: 0.6217 - loss: 1.0367 - top-5-accuracy: 0.9580

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 559ms/step - accuracy: 0.6235 - loss: 1.0325 - top-5-accuracy: 0.9589

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 559ms/step - accuracy: 0.6251 - loss: 1.0275 - top-5-accuracy: 0.9599

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 559ms/step - accuracy: 0.6261 - loss: 1.0232 - top-5-accuracy: 0.9606 

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 558ms/step - accuracy: 0.6268 - loss: 1.0194 - top-5-accuracy: 0.9613

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 558ms/step - accuracy: 0.6279 - loss: 1.0155 - top-5-accuracy: 0.9620

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 557ms/step - accuracy: 0.6285 - loss: 1.0133 - top-5-accuracy: 0.9625

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 556ms/step - accuracy: 0.6288 - loss: 1.0118 - top-5-accuracy: 0.9629

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 555ms/step - accuracy: 0.6289 - loss: 1.0106 - top-5-accuracy: 0.9633

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 555ms/step - accuracy: 0.6292 - loss: 1.0090 - top-5-accuracy: 0.9637

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 554ms/step - accuracy: 0.6297 - loss: 1.0075 - top-5-accuracy: 0.9641

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 554ms/step - accuracy: 0.6300 - loss: 1.0063 - top-5-accuracy: 0.9644

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 554ms/step - accuracy: 0.6304 - loss: 1.0049 - top-5-accuracy: 0.9648

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 553ms/step - accuracy: 0.6307 - loss: 1.0037 - top-5-accuracy: 0.9651

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 553ms/step - accuracy: 0.6309 - loss: 1.0027 - top-5-accuracy: 0.9655

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 552ms/step - accuracy: 0.6310 - loss: 1.0018 - top-5-accuracy: 0.9658

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 552ms/step - accuracy: 0.6315 - loss: 1.0003 - top-5-accuracy: 0.9661

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 551ms/step - accuracy: 0.6318 - loss: 0.9990 - top-5-accuracy: 0.9664

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 551ms/step - accuracy: 0.6321 - loss: 0.9979 - top-5-accuracy: 0.9667

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 551ms/step - accuracy: 0.6325 - loss: 0.9965 - top-5-accuracy: 0.9670

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 540ms/step - accuracy: 0.6330 - loss: 0.9949 - top-5-accuracy: 0.9673

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 583ms/step - accuracy: 0.6334 - loss: 0.9933 - top-5-accuracy: 0.9676 - val_accuracy: 0.7019 - val_loss: 0.8714 - val_top-5-accuracy: 0.9565


<div class="k-default-codeblock">
```
Epoch 34/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 559ms/step - accuracy: 0.6250 - loss: 0.9175 - top-5-accuracy: 0.9375

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.6641 - loss: 0.9147 - top-5-accuracy: 0.9453

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 548ms/step - accuracy: 0.6753 - loss: 0.9137 - top-5-accuracy: 0.9531

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.6823 - loss: 0.8992 - top-5-accuracy: 0.9590

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.6833 - loss: 0.8962 - top-5-accuracy: 0.9622

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.6832 - loss: 0.8928 - top-5-accuracy: 0.9650

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.6831 - loss: 0.8877 - top-5-accuracy: 0.9675

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.6852 - loss: 0.8835 - top-5-accuracy: 0.9696

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.6870 - loss: 0.8803 - top-5-accuracy: 0.9710

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.6892 - loss: 0.8770 - top-5-accuracy: 0.9724

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.6906 - loss: 0.8742 - top-5-accuracy: 0.9736

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.6919 - loss: 0.8724 - top-5-accuracy: 0.9747

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.6937 - loss: 0.8696 - top-5-accuracy: 0.9755 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.6957 - loss: 0.8672 - top-5-accuracy: 0.9763

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.6976 - loss: 0.8643 - top-5-accuracy: 0.9771

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.6998 - loss: 0.8614 - top-5-accuracy: 0.9778

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.7017 - loss: 0.8595 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.7035 - loss: 0.8573 - top-5-accuracy: 0.9787

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.7048 - loss: 0.8561 - top-5-accuracy: 0.9790

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.7058 - loss: 0.8552 - top-5-accuracy: 0.9793

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.7069 - loss: 0.8541 - top-5-accuracy: 0.9797

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.7078 - loss: 0.8529 - top-5-accuracy: 0.9800

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7086 - loss: 0.8519 - top-5-accuracy: 0.9804

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.7095 - loss: 0.8508 - top-5-accuracy: 0.9806

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.7100 - loss: 0.8505 - top-5-accuracy: 0.9808

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 546ms/step - accuracy: 0.7104 - loss: 0.8500 - top-5-accuracy: 0.9809

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.7107 - loss: 0.8496 - top-5-accuracy: 0.9811

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.7109 - loss: 0.8492 - top-5-accuracy: 0.9812

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.7111 - loss: 0.8487 - top-5-accuracy: 0.9814

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.7114 - loss: 0.8480 - top-5-accuracy: 0.9816

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.7117 - loss: 0.8473 - top-5-accuracy: 0.9817

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.7120 - loss: 0.8467 - top-5-accuracy: 0.9819 - val_accuracy: 0.6708 - val_loss: 0.7280 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 35/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  18s 620ms/step - accuracy: 0.6875 - loss: 0.8665 - top-5-accuracy: 0.9062

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.7188 - loss: 0.7992 - top-5-accuracy: 0.9297

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.7222 - loss: 0.7852 - top-5-accuracy: 0.9427

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.7155 - loss: 0.8118 - top-5-accuracy: 0.9492

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.7174 - loss: 0.8176 - top-5-accuracy: 0.9544

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.7176 - loss: 0.8188 - top-5-accuracy: 0.9585

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.7165 - loss: 0.8248 - top-5-accuracy: 0.9619

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 544ms/step - accuracy: 0.7163 - loss: 0.8277 - top-5-accuracy: 0.9647

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.7146 - loss: 0.8337 - top-5-accuracy: 0.9671

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.7141 - loss: 0.8359 - top-5-accuracy: 0.9691

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.7132 - loss: 0.8392 - top-5-accuracy: 0.9709

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.7131 - loss: 0.8408 - top-5-accuracy: 0.9724

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 544ms/step - accuracy: 0.7129 - loss: 0.8426 - top-5-accuracy: 0.9738 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 544ms/step - accuracy: 0.7130 - loss: 0.8448 - top-5-accuracy: 0.9747

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 544ms/step - accuracy: 0.7129 - loss: 0.8468 - top-5-accuracy: 0.9756

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.7121 - loss: 0.8494 - top-5-accuracy: 0.9761

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.7115 - loss: 0.8513 - top-5-accuracy: 0.9766

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.7108 - loss: 0.8532 - top-5-accuracy: 0.9769

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.7097 - loss: 0.8556 - top-5-accuracy: 0.9772

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 544ms/step - accuracy: 0.7085 - loss: 0.8580 - top-5-accuracy: 0.9775

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.7073 - loss: 0.8605 - top-5-accuracy: 0.9777

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.7064 - loss: 0.8624 - top-5-accuracy: 0.9779

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.7054 - loss: 0.8640 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.7045 - loss: 0.8655 - top-5-accuracy: 0.9784

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 544ms/step - accuracy: 0.7037 - loss: 0.8665 - top-5-accuracy: 0.9787

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.7031 - loss: 0.8673 - top-5-accuracy: 0.9790

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.7023 - loss: 0.8683 - top-5-accuracy: 0.9792

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7017 - loss: 0.8690 - top-5-accuracy: 0.9795

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7013 - loss: 0.8696 - top-5-accuracy: 0.9797

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.7007 - loss: 0.8703 - top-5-accuracy: 0.9799

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.7001 - loss: 0.8711 - top-5-accuracy: 0.9801

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.6995 - loss: 0.8717 - top-5-accuracy: 0.9803 - val_accuracy: 0.7578 - val_loss: 0.7625 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 36/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 552ms/step - accuracy: 0.8125 - loss: 0.7243 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 539ms/step - accuracy: 0.7578 - loss: 0.8375 - top-5-accuracy: 0.9922

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.7344 - loss: 0.8640 - top-5-accuracy: 0.9878

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 541ms/step - accuracy: 0.7109 - loss: 0.8940 - top-5-accuracy: 0.9870

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 541ms/step - accuracy: 0.6938 - loss: 0.9151 - top-5-accuracy: 0.9858

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 541ms/step - accuracy: 0.6823 - loss: 0.9388 - top-5-accuracy: 0.9830

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 542ms/step - accuracy: 0.6786 - loss: 0.9463 - top-5-accuracy: 0.9816

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 543ms/step - accuracy: 0.6777 - loss: 0.9497 - top-5-accuracy: 0.9805

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.6777 - loss: 0.9493 - top-5-accuracy: 0.9799

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.6777 - loss: 0.9496 - top-5-accuracy: 0.9794

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.6783 - loss: 0.9493 - top-5-accuracy: 0.9793

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.6798 - loss: 0.9468 - top-5-accuracy: 0.9790

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.6818 - loss: 0.9438 - top-5-accuracy: 0.9788 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.6838 - loss: 0.9408 - top-5-accuracy: 0.9786

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.6862 - loss: 0.9377 - top-5-accuracy: 0.9783

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.6883 - loss: 0.9346 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.6904 - loss: 0.9320 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 544ms/step - accuracy: 0.6920 - loss: 0.9300 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 544ms/step - accuracy: 0.6937 - loss: 0.9277 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.6948 - loss: 0.9259 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.6957 - loss: 0.9247 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.6965 - loss: 0.9236 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.6970 - loss: 0.9225 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.6977 - loss: 0.9210 - top-5-accuracy: 0.9780

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.6981 - loss: 0.9197 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.6984 - loss: 0.9186 - top-5-accuracy: 0.9780

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.6986 - loss: 0.9173 - top-5-accuracy: 0.9780

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.6987 - loss: 0.9163 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.6987 - loss: 0.9152 - top-5-accuracy: 0.9781

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.6987 - loss: 0.9140 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.6989 - loss: 0.9124 - top-5-accuracy: 0.9782

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.6991 - loss: 0.9108 - top-5-accuracy: 0.9782 - val_accuracy: 0.6832 - val_loss: 0.9947 - val_top-5-accuracy: 1.0000


<div class="k-default-codeblock">
```
Epoch 37/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  18s 620ms/step - accuracy: 0.6875 - loss: 0.9376 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 607ms/step - accuracy: 0.6953 - loss: 0.9423 - top-5-accuracy: 0.9844

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  16s 576ms/step - accuracy: 0.6892 - loss: 0.9353 - top-5-accuracy: 0.9826

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  15s 563ms/step - accuracy: 0.6868 - loss: 0.9284 - top-5-accuracy: 0.9811

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 560ms/step - accuracy: 0.6832 - loss: 0.9268 - top-5-accuracy: 0.9799

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 557ms/step - accuracy: 0.6848 - loss: 0.9215 - top-5-accuracy: 0.9798

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 556ms/step - accuracy: 0.6890 - loss: 0.9136 - top-5-accuracy: 0.9801

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 554ms/step - accuracy: 0.6932 - loss: 0.9058 - top-5-accuracy: 0.9806

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 553ms/step - accuracy: 0.6953 - loss: 0.8990 - top-5-accuracy: 0.9813

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 553ms/step - accuracy: 0.6976 - loss: 0.8915 - top-5-accuracy: 0.9819

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 551ms/step - accuracy: 0.6990 - loss: 0.8854 - top-5-accuracy: 0.9825

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.7005 - loss: 0.8804 - top-5-accuracy: 0.9826

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 548ms/step - accuracy: 0.7021 - loss: 0.8754 - top-5-accuracy: 0.9829 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 548ms/step - accuracy: 0.7039 - loss: 0.8708 - top-5-accuracy: 0.9830

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 547ms/step - accuracy: 0.7057 - loss: 0.8667 - top-5-accuracy: 0.9830

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 547ms/step - accuracy: 0.7070 - loss: 0.8636 - top-5-accuracy: 0.9831

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.7082 - loss: 0.8607 - top-5-accuracy: 0.9832

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.7097 - loss: 0.8581 - top-5-accuracy: 0.9834

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.7110 - loss: 0.8558 - top-5-accuracy: 0.9835

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.7121 - loss: 0.8537 - top-5-accuracy: 0.9835

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.7132 - loss: 0.8519 - top-5-accuracy: 0.9835

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7141 - loss: 0.8503 - top-5-accuracy: 0.9836

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7146 - loss: 0.8495 - top-5-accuracy: 0.9836

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.7149 - loss: 0.8486 - top-5-accuracy: 0.9837

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.7154 - loss: 0.8475 - top-5-accuracy: 0.9838

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.7160 - loss: 0.8460 - top-5-accuracy: 0.9839

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.7164 - loss: 0.8449 - top-5-accuracy: 0.9840

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7170 - loss: 0.8440 - top-5-accuracy: 0.9841

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7174 - loss: 0.8433 - top-5-accuracy: 0.9842

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.7178 - loss: 0.8423 - top-5-accuracy: 0.9843

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.7183 - loss: 0.8412 - top-5-accuracy: 0.9844

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.7187 - loss: 0.8401 - top-5-accuracy: 0.9845 - val_accuracy: 0.6087 - val_loss: 0.9812 - val_top-5-accuracy: 0.9752


<div class="k-default-codeblock">
```
Epoch 38/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 558ms/step - accuracy: 0.7500 - loss: 0.8003 - top-5-accuracy: 0.9688

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  16s 552ms/step - accuracy: 0.7344 - loss: 0.8521 - top-5-accuracy: 0.9766

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.7222 - loss: 0.8880 - top-5-accuracy: 0.9740

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.7096 - loss: 0.9141 - top-5-accuracy: 0.9727

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.7027 - loss: 0.9312 - top-5-accuracy: 0.9719

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.6984 - loss: 0.9407 - top-5-accuracy: 0.9705

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.6943 - loss: 0.9469 - top-5-accuracy: 0.9702

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.6940 - loss: 0.9441 - top-5-accuracy: 0.9705

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.6936 - loss: 0.9395 - top-5-accuracy: 0.9711

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.6949 - loss: 0.9336 - top-5-accuracy: 0.9718

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.6976 - loss: 0.9266 - top-5-accuracy: 0.9726

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.6993 - loss: 0.9206 - top-5-accuracy: 0.9733

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.7010 - loss: 0.9148 - top-5-accuracy: 0.9741 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.7023 - loss: 0.9092 - top-5-accuracy: 0.9748

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.7030 - loss: 0.9053 - top-5-accuracy: 0.9753

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.7038 - loss: 0.9008 - top-5-accuracy: 0.9757

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.7047 - loss: 0.8961 - top-5-accuracy: 0.9762

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.7059 - loss: 0.8911 - top-5-accuracy: 0.9766

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.7070 - loss: 0.8870 - top-5-accuracy: 0.9770

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.7079 - loss: 0.8836 - top-5-accuracy: 0.9774

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.7089 - loss: 0.8800 - top-5-accuracy: 0.9777

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.7099 - loss: 0.8769 - top-5-accuracy: 0.9780

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.7106 - loss: 0.8740 - top-5-accuracy: 0.9783

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.7111 - loss: 0.8716 - top-5-accuracy: 0.9786

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.7118 - loss: 0.8690 - top-5-accuracy: 0.9789

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.7125 - loss: 0.8666 - top-5-accuracy: 0.9792

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.7132 - loss: 0.8642 - top-5-accuracy: 0.9795

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7140 - loss: 0.8616 - top-5-accuracy: 0.9798

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7148 - loss: 0.8592 - top-5-accuracy: 0.9801

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.7155 - loss: 0.8568 - top-5-accuracy: 0.9804

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.7164 - loss: 0.8542 - top-5-accuracy: 0.9806

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.7171 - loss: 0.8518 - top-5-accuracy: 0.9808 - val_accuracy: 0.6273 - val_loss: 0.8479 - val_top-5-accuracy: 0.9752


<div class="k-default-codeblock">
```
Epoch 39/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 556ms/step - accuracy: 0.7812 - loss: 0.6104 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 542ms/step - accuracy: 0.7812 - loss: 0.6495 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 549ms/step - accuracy: 0.7674 - loss: 0.6888 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 549ms/step - accuracy: 0.7591 - loss: 0.7025 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 553ms/step - accuracy: 0.7460 - loss: 0.7306 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 551ms/step - accuracy: 0.7363 - loss: 0.7515 - top-5-accuracy: 0.9991

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 550ms/step - accuracy: 0.7306 - loss: 0.7663 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 550ms/step - accuracy: 0.7276 - loss: 0.7747 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 549ms/step - accuracy: 0.7247 - loss: 0.7818 - top-5-accuracy: 0.9964

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 549ms/step - accuracy: 0.7229 - loss: 0.7851 - top-5-accuracy: 0.9958

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.7215 - loss: 0.7879 - top-5-accuracy: 0.9952

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 548ms/step - accuracy: 0.7204 - loss: 0.7892 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 548ms/step - accuracy: 0.7204 - loss: 0.7884 - top-5-accuracy: 0.9944 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 548ms/step - accuracy: 0.7210 - loss: 0.7872 - top-5-accuracy: 0.9941

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 547ms/step - accuracy: 0.7216 - loss: 0.7864 - top-5-accuracy: 0.9937

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.7223 - loss: 0.7861 - top-5-accuracy: 0.9934

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.7230 - loss: 0.7858 - top-5-accuracy: 0.9931

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 547ms/step - accuracy: 0.7238 - loss: 0.7849 - top-5-accuracy: 0.9928

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.7247 - loss: 0.7842 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.7254 - loss: 0.7833 - top-5-accuracy: 0.9922

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 547ms/step - accuracy: 0.7262 - loss: 0.7824 - top-5-accuracy: 0.9920

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7273 - loss: 0.7811 - top-5-accuracy: 0.9917

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7281 - loss: 0.7798 - top-5-accuracy: 0.9915

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.7284 - loss: 0.7793 - top-5-accuracy: 0.9912

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.7287 - loss: 0.7787 - top-5-accuracy: 0.9910

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 546ms/step - accuracy: 0.7291 - loss: 0.7779 - top-5-accuracy: 0.9908

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.7295 - loss: 0.7770 - top-5-accuracy: 0.9906

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.7298 - loss: 0.7763 - top-5-accuracy: 0.9905

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.7302 - loss: 0.7753 - top-5-accuracy: 0.9903

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.7307 - loss: 0.7741 - top-5-accuracy: 0.9902

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.7311 - loss: 0.7727 - top-5-accuracy: 0.9902

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 579ms/step - accuracy: 0.7315 - loss: 0.7714 - top-5-accuracy: 0.9901 - val_accuracy: 0.6522 - val_loss: 0.8158 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 40/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 554ms/step - accuracy: 0.7188 - loss: 0.8603 - top-5-accuracy: 0.9688

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 543ms/step - accuracy: 0.7109 - loss: 0.8222 - top-5-accuracy: 0.9766

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.7135 - loss: 0.7934 - top-5-accuracy: 0.9809

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.7168 - loss: 0.7860 - top-5-accuracy: 0.9818

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.7184 - loss: 0.7851 - top-5-accuracy: 0.9829

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.7194 - loss: 0.7877 - top-5-accuracy: 0.9840

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.7212 - loss: 0.7862 - top-5-accuracy: 0.9850

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.7238 - loss: 0.7820 - top-5-accuracy: 0.9859

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.7252 - loss: 0.7791 - top-5-accuracy: 0.9863

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.7267 - loss: 0.7756 - top-5-accuracy: 0.9868

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.7283 - loss: 0.7724 - top-5-accuracy: 0.9869

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.7308 - loss: 0.7676 - top-5-accuracy: 0.9872

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.7339 - loss: 0.7623 - top-5-accuracy: 0.9874 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.7359 - loss: 0.7585 - top-5-accuracy: 0.9875

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 546ms/step - accuracy: 0.7372 - loss: 0.7555 - top-5-accuracy: 0.9876

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.7389 - loss: 0.7524 - top-5-accuracy: 0.9877

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.7404 - loss: 0.7496 - top-5-accuracy: 0.9878

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.7420 - loss: 0.7469 - top-5-accuracy: 0.9879

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.7438 - loss: 0.7436 - top-5-accuracy: 0.9880

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.7456 - loss: 0.7404 - top-5-accuracy: 0.9881

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.7473 - loss: 0.7376 - top-5-accuracy: 0.9882

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.7490 - loss: 0.7352 - top-5-accuracy: 0.9882

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.7504 - loss: 0.7334 - top-5-accuracy: 0.9882

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.7517 - loss: 0.7317 - top-5-accuracy: 0.9883

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.7526 - loss: 0.7304 - top-5-accuracy: 0.9884

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.7535 - loss: 0.7292 - top-5-accuracy: 0.9884

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.7541 - loss: 0.7282 - top-5-accuracy: 0.9885

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7548 - loss: 0.7272 - top-5-accuracy: 0.9886

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.7555 - loss: 0.7264 - top-5-accuracy: 0.9887

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.7562 - loss: 0.7256 - top-5-accuracy: 0.9888

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.7567 - loss: 0.7249 - top-5-accuracy: 0.9888

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.7573 - loss: 0.7242 - top-5-accuracy: 0.9889 - val_accuracy: 0.7391 - val_loss: 0.7397 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 41/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 562ms/step - accuracy: 0.8125 - loss: 0.7093 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.8281 - loss: 0.6488 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 546ms/step - accuracy: 0.8160 - loss: 0.6370 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.7956 - loss: 0.6786 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.7827 - loss: 0.6956 - top-5-accuracy: 0.9972

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.7773 - loss: 0.7027 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.7695 - loss: 0.7083 - top-5-accuracy: 0.9966

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.7661 - loss: 0.7111 - top-5-accuracy: 0.9956

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.7636 - loss: 0.7142 - top-5-accuracy: 0.9949

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.7616 - loss: 0.7162 - top-5-accuracy: 0.9945

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.7605 - loss: 0.7163 - top-5-accuracy: 0.9942

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.7607 - loss: 0.7144 - top-5-accuracy: 0.9938

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 547ms/step - accuracy: 0.7614 - loss: 0.7132 - top-5-accuracy: 0.9936 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 547ms/step - accuracy: 0.7618 - loss: 0.7122 - top-5-accuracy: 0.9932

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 547ms/step - accuracy: 0.7627 - loss: 0.7107 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 547ms/step - accuracy: 0.7636 - loss: 0.7087 - top-5-accuracy: 0.9928

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 547ms/step - accuracy: 0.7643 - loss: 0.7078 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 547ms/step - accuracy: 0.7648 - loss: 0.7068 - top-5-accuracy: 0.9922

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.7653 - loss: 0.7058 - top-5-accuracy: 0.9920

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.7657 - loss: 0.7049 - top-5-accuracy: 0.9919

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 547ms/step - accuracy: 0.7663 - loss: 0.7038 - top-5-accuracy: 0.9918

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7669 - loss: 0.7025 - top-5-accuracy: 0.9917

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.7675 - loss: 0.7012 - top-5-accuracy: 0.9916

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.7680 - loss: 0.7000 - top-5-accuracy: 0.9915

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.7685 - loss: 0.6988 - top-5-accuracy: 0.9914

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 547ms/step - accuracy: 0.7690 - loss: 0.6975 - top-5-accuracy: 0.9913

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 548ms/step - accuracy: 0.7695 - loss: 0.6964 - top-5-accuracy: 0.9913

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 549ms/step - accuracy: 0.7697 - loss: 0.6955 - top-5-accuracy: 0.9912

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 549ms/step - accuracy: 0.7701 - loss: 0.6943 - top-5-accuracy: 0.9912

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 548ms/step - accuracy: 0.7705 - loss: 0.6928 - top-5-accuracy: 0.9912

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 538ms/step - accuracy: 0.7710 - loss: 0.6912 - top-5-accuracy: 0.9912

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 581ms/step - accuracy: 0.7715 - loss: 0.6897 - top-5-accuracy: 0.9912 - val_accuracy: 0.7329 - val_loss: 0.6664 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 42/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 555ms/step - accuracy: 0.7188 - loss: 0.7727 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 549ms/step - accuracy: 0.7344 - loss: 0.7328 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 549ms/step - accuracy: 0.7500 - loss: 0.6959 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 548ms/step - accuracy: 0.7578 - loss: 0.6849 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.7638 - loss: 0.6815 - top-5-accuracy: 0.9972

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.7693 - loss: 0.6752 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.7748 - loss: 0.6671 - top-5-accuracy: 0.9966

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 544ms/step - accuracy: 0.7785 - loss: 0.6607 - top-5-accuracy: 0.9961

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.7831 - loss: 0.6533 - top-5-accuracy: 0.9957

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.7876 - loss: 0.6452 - top-5-accuracy: 0.9955

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.7914 - loss: 0.6386 - top-5-accuracy: 0.9954

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.7951 - loss: 0.6323 - top-5-accuracy: 0.9954

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.7977 - loss: 0.6283 - top-5-accuracy: 0.9954 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8004 - loss: 0.6245 - top-5-accuracy: 0.9954

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.8026 - loss: 0.6218 - top-5-accuracy: 0.9953

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8044 - loss: 0.6199 - top-5-accuracy: 0.9951

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8060 - loss: 0.6181 - top-5-accuracy: 0.9949

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.8074 - loss: 0.6160 - top-5-accuracy: 0.9948

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.8085 - loss: 0.6147 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.8094 - loss: 0.6135 - top-5-accuracy: 0.9945

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8103 - loss: 0.6122 - top-5-accuracy: 0.9944

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.8112 - loss: 0.6108 - top-5-accuracy: 0.9944

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8120 - loss: 0.6095 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.8125 - loss: 0.6086 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 544ms/step - accuracy: 0.8127 - loss: 0.6082 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 544ms/step - accuracy: 0.8131 - loss: 0.6075 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8135 - loss: 0.6067 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.8140 - loss: 0.6056 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8144 - loss: 0.6047 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8148 - loss: 0.6038 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.8153 - loss: 0.6028 - top-5-accuracy: 0.9943

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8157 - loss: 0.6019 - top-5-accuracy: 0.9943 - val_accuracy: 0.7888 - val_loss: 0.5880 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 43/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 563ms/step - accuracy: 0.7500 - loss: 0.7233 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 541ms/step - accuracy: 0.7656 - loss: 0.6590 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 552ms/step - accuracy: 0.7639 - loss: 0.6364 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  15s 566ms/step - accuracy: 0.7624 - loss: 0.6347 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 555ms/step - accuracy: 0.7574 - loss: 0.6472 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 553ms/step - accuracy: 0.7570 - loss: 0.6498 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 553ms/step - accuracy: 0.7579 - loss: 0.6503 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 552ms/step - accuracy: 0.7604 - loss: 0.6488 - top-5-accuracy: 0.9975

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 551ms/step - accuracy: 0.7611 - loss: 0.6525 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 551ms/step - accuracy: 0.7619 - loss: 0.6549 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 551ms/step - accuracy: 0.7634 - loss: 0.6555 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 551ms/step - accuracy: 0.7653 - loss: 0.6546 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 550ms/step - accuracy: 0.7669 - loss: 0.6539 - top-5-accuracy: 0.9974 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 550ms/step - accuracy: 0.7686 - loss: 0.6530 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 549ms/step - accuracy: 0.7703 - loss: 0.6512 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 549ms/step - accuracy: 0.7712 - loss: 0.6507 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 549ms/step - accuracy: 0.7720 - loss: 0.6500 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 549ms/step - accuracy: 0.7727 - loss: 0.6491 - top-5-accuracy: 0.9972

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 549ms/step - accuracy: 0.7732 - loss: 0.6484 - top-5-accuracy: 0.9972

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 549ms/step - accuracy: 0.7737 - loss: 0.6476 - top-5-accuracy: 0.9972

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 548ms/step - accuracy: 0.7741 - loss: 0.6469 - top-5-accuracy: 0.9971

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 548ms/step - accuracy: 0.7746 - loss: 0.6462 - top-5-accuracy: 0.9970

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 548ms/step - accuracy: 0.7754 - loss: 0.6450 - top-5-accuracy: 0.9969

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 548ms/step - accuracy: 0.7760 - loss: 0.6442 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 547ms/step - accuracy: 0.7767 - loss: 0.6432 - top-5-accuracy: 0.9965

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 547ms/step - accuracy: 0.7772 - loss: 0.6425 - top-5-accuracy: 0.9964

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 547ms/step - accuracy: 0.7776 - loss: 0.6417 - top-5-accuracy: 0.9963

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 547ms/step - accuracy: 0.7781 - loss: 0.6408 - top-5-accuracy: 0.9961

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 547ms/step - accuracy: 0.7785 - loss: 0.6398 - top-5-accuracy: 0.9961

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 547ms/step - accuracy: 0.7791 - loss: 0.6386 - top-5-accuracy: 0.9960

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 536ms/step - accuracy: 0.7797 - loss: 0.6376 - top-5-accuracy: 0.9959

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 579ms/step - accuracy: 0.7802 - loss: 0.6367 - top-5-accuracy: 0.9958 - val_accuracy: 0.7453 - val_loss: 0.6631 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 44/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 560ms/step - accuracy: 0.7188 - loss: 0.7368 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.7656 - loss: 0.6702 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 548ms/step - accuracy: 0.7743 - loss: 0.6476 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.7799 - loss: 0.6407 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 551ms/step - accuracy: 0.7865 - loss: 0.6321 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 550ms/step - accuracy: 0.7856 - loss: 0.6417 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 549ms/step - accuracy: 0.7875 - loss: 0.6422 - top-5-accuracy: 0.9959

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 549ms/step - accuracy: 0.7897 - loss: 0.6401 - top-5-accuracy: 0.9949

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 550ms/step - accuracy: 0.7895 - loss: 0.6403 - top-5-accuracy: 0.9939

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 550ms/step - accuracy: 0.7877 - loss: 0.6438 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 550ms/step - accuracy: 0.7866 - loss: 0.6466 - top-5-accuracy: 0.9923

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 550ms/step - accuracy: 0.7858 - loss: 0.6482 - top-5-accuracy: 0.9919

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 549ms/step - accuracy: 0.7852 - loss: 0.6500 - top-5-accuracy: 0.9912 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 548ms/step - accuracy: 0.7854 - loss: 0.6498 - top-5-accuracy: 0.9907

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 548ms/step - accuracy: 0.7853 - loss: 0.6503 - top-5-accuracy: 0.9904

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 548ms/step - accuracy: 0.7855 - loss: 0.6501 - top-5-accuracy: 0.9900

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 547ms/step - accuracy: 0.7861 - loss: 0.6495 - top-5-accuracy: 0.9897

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 548ms/step - accuracy: 0.7868 - loss: 0.6485 - top-5-accuracy: 0.9895

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 548ms/step - accuracy: 0.7873 - loss: 0.6484 - top-5-accuracy: 0.9892

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.7877 - loss: 0.6483 - top-5-accuracy: 0.9890

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 547ms/step - accuracy: 0.7881 - loss: 0.6478 - top-5-accuracy: 0.9888

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 548ms/step - accuracy: 0.7886 - loss: 0.6470 - top-5-accuracy: 0.9886

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.7891 - loss: 0.6461 - top-5-accuracy: 0.9885

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 547ms/step - accuracy: 0.7896 - loss: 0.6450 - top-5-accuracy: 0.9885

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 547ms/step - accuracy: 0.7900 - loss: 0.6440 - top-5-accuracy: 0.9884

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 547ms/step - accuracy: 0.7903 - loss: 0.6430 - top-5-accuracy: 0.9884

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 547ms/step - accuracy: 0.7907 - loss: 0.6421 - top-5-accuracy: 0.9883

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 547ms/step - accuracy: 0.7911 - loss: 0.6409 - top-5-accuracy: 0.9883

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 547ms/step - accuracy: 0.7915 - loss: 0.6397 - top-5-accuracy: 0.9883

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 547ms/step - accuracy: 0.7920 - loss: 0.6384 - top-5-accuracy: 0.9883

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 537ms/step - accuracy: 0.7925 - loss: 0.6369 - top-5-accuracy: 0.9883

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 580ms/step - accuracy: 0.7930 - loss: 0.6356 - top-5-accuracy: 0.9883 - val_accuracy: 0.7453 - val_loss: 0.6834 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 45/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 569ms/step - accuracy: 0.8125 - loss: 0.6084 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.7891 - loss: 0.6015 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.7865 - loss: 0.6022 - top-5-accuracy: 0.9965

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.7930 - loss: 0.5918 - top-5-accuracy: 0.9954

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.8019 - loss: 0.5736 - top-5-accuracy: 0.9951

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.8071 - loss: 0.5659 - top-5-accuracy: 0.9942

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.8111 - loss: 0.5601 - top-5-accuracy: 0.9937

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.8132 - loss: 0.5567 - top-5-accuracy: 0.9935

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.8135 - loss: 0.5557 - top-5-accuracy: 0.9935

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.8134 - loss: 0.5543 - top-5-accuracy: 0.9935

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.8131 - loss: 0.5531 - top-5-accuracy: 0.9936

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.8128 - loss: 0.5518 - top-5-accuracy: 0.9937

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.8126 - loss: 0.5511 - top-5-accuracy: 0.9938 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 546ms/step - accuracy: 0.8121 - loss: 0.5506 - top-5-accuracy: 0.9938

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 546ms/step - accuracy: 0.8120 - loss: 0.5503 - top-5-accuracy: 0.9936

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.8120 - loss: 0.5498 - top-5-accuracy: 0.9934

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8122 - loss: 0.5491 - top-5-accuracy: 0.9933

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.8124 - loss: 0.5487 - top-5-accuracy: 0.9931

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.8127 - loss: 0.5480 - top-5-accuracy: 0.9929

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.8129 - loss: 0.5477 - top-5-accuracy: 0.9928

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8133 - loss: 0.5472 - top-5-accuracy: 0.9927

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8136 - loss: 0.5469 - top-5-accuracy: 0.9927

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8138 - loss: 0.5467 - top-5-accuracy: 0.9926

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8140 - loss: 0.5467 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8143 - loss: 0.5466 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8144 - loss: 0.5465 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8147 - loss: 0.5462 - top-5-accuracy: 0.9924

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8151 - loss: 0.5456 - top-5-accuracy: 0.9924

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8154 - loss: 0.5452 - top-5-accuracy: 0.9924

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8156 - loss: 0.5449 - top-5-accuracy: 0.9924

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.8159 - loss: 0.5444 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8162 - loss: 0.5439 - top-5-accuracy: 0.9925 - val_accuracy: 0.7640 - val_loss: 0.5521 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 46/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 559ms/step - accuracy: 0.7500 - loss: 0.5392 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 542ms/step - accuracy: 0.7500 - loss: 0.5489 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 542ms/step - accuracy: 0.7639 - loss: 0.5346 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 542ms/step - accuracy: 0.7741 - loss: 0.5281 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 542ms/step - accuracy: 0.7830 - loss: 0.5199 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.7879 - loss: 0.5189 - top-5-accuracy: 0.9991

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.7895 - loss: 0.5232 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 543ms/step - accuracy: 0.7934 - loss: 0.5222 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.7959 - loss: 0.5234 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.7988 - loss: 0.5225 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.8008 - loss: 0.5220 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.8029 - loss: 0.5214 - top-5-accuracy: 0.9976

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 543ms/step - accuracy: 0.8053 - loss: 0.5201 - top-5-accuracy: 0.9973 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 544ms/step - accuracy: 0.8069 - loss: 0.5202 - top-5-accuracy: 0.9970

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 544ms/step - accuracy: 0.8085 - loss: 0.5199 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 543ms/step - accuracy: 0.8102 - loss: 0.5188 - top-5-accuracy: 0.9966

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 543ms/step - accuracy: 0.8120 - loss: 0.5177 - top-5-accuracy: 0.9965

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 544ms/step - accuracy: 0.8137 - loss: 0.5164 - top-5-accuracy: 0.9964

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 544ms/step - accuracy: 0.8153 - loss: 0.5152 - top-5-accuracy: 0.9963

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 544ms/step - accuracy: 0.8164 - loss: 0.5145 - top-5-accuracy: 0.9962

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 544ms/step - accuracy: 0.8176 - loss: 0.5137 - top-5-accuracy: 0.9960

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.8186 - loss: 0.5131 - top-5-accuracy: 0.9959

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.8195 - loss: 0.5124 - top-5-accuracy: 0.9958

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.8204 - loss: 0.5116 - top-5-accuracy: 0.9957

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 544ms/step - accuracy: 0.8210 - loss: 0.5113 - top-5-accuracy: 0.9955

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 544ms/step - accuracy: 0.8216 - loss: 0.5109 - top-5-accuracy: 0.9954

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 544ms/step - accuracy: 0.8222 - loss: 0.5104 - top-5-accuracy: 0.9953

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.8228 - loss: 0.5098 - top-5-accuracy: 0.9953

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.8235 - loss: 0.5093 - top-5-accuracy: 0.9952

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 544ms/step - accuracy: 0.8240 - loss: 0.5089 - top-5-accuracy: 0.9952

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 533ms/step - accuracy: 0.8246 - loss: 0.5082 - top-5-accuracy: 0.9951

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 576ms/step - accuracy: 0.8251 - loss: 0.5077 - top-5-accuracy: 0.9951 - val_accuracy: 0.7702 - val_loss: 0.5984 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 47/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 555ms/step - accuracy: 0.8750 - loss: 0.4394 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.8750 - loss: 0.4638 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.8681 - loss: 0.4589 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.8561 - loss: 0.4717 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.8511 - loss: 0.4758 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.8490 - loss: 0.4779 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.8457 - loss: 0.4811 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.8445 - loss: 0.4809 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8437 - loss: 0.4812 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8440 - loss: 0.4800 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.8440 - loss: 0.4794 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.8431 - loss: 0.4805 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 544ms/step - accuracy: 0.8431 - loss: 0.4806 - top-5-accuracy: 1.0000 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 544ms/step - accuracy: 0.8433 - loss: 0.4806 - top-5-accuracy: 0.9998

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 544ms/step - accuracy: 0.8441 - loss: 0.4802 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8446 - loss: 0.4803 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8448 - loss: 0.4812 - top-5-accuracy: 0.9993

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.8451 - loss: 0.4815 - top-5-accuracy: 0.9991

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.8452 - loss: 0.4819 - top-5-accuracy: 0.9990

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.8456 - loss: 0.4818 - top-5-accuracy: 0.9989

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8461 - loss: 0.4817 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8465 - loss: 0.4821 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8467 - loss: 0.4824 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8468 - loss: 0.4830 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8471 - loss: 0.4832 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8473 - loss: 0.4836 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8475 - loss: 0.4837 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8477 - loss: 0.4836 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8478 - loss: 0.4836 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 544ms/step - accuracy: 0.8481 - loss: 0.4832 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.8485 - loss: 0.4827 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8488 - loss: 0.4822 - top-5-accuracy: 0.9977 - val_accuracy: 0.7391 - val_loss: 0.6498 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 48/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 553ms/step - accuracy: 0.8438 - loss: 0.4953 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 551ms/step - accuracy: 0.8047 - loss: 0.5172 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 548ms/step - accuracy: 0.8073 - loss: 0.5186 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.8125 - loss: 0.5279 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 554ms/step - accuracy: 0.8138 - loss: 0.5306 - top-5-accuracy: 0.9972

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 553ms/step - accuracy: 0.8170 - loss: 0.5293 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 552ms/step - accuracy: 0.8196 - loss: 0.5266 - top-5-accuracy: 0.9966

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 552ms/step - accuracy: 0.8231 - loss: 0.5227 - top-5-accuracy: 0.9965

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 551ms/step - accuracy: 0.8261 - loss: 0.5185 - top-5-accuracy: 0.9965

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 550ms/step - accuracy: 0.8292 - loss: 0.5147 - top-5-accuracy: 0.9966

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 550ms/step - accuracy: 0.8315 - loss: 0.5111 - top-5-accuracy: 0.9966

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 549ms/step - accuracy: 0.8338 - loss: 0.5073 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 548ms/step - accuracy: 0.8359 - loss: 0.5042 - top-5-accuracy: 0.9966 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 548ms/step - accuracy: 0.8374 - loss: 0.5022 - top-5-accuracy: 0.9963

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 548ms/step - accuracy: 0.8388 - loss: 0.5006 - top-5-accuracy: 0.9960

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 548ms/step - accuracy: 0.8400 - loss: 0.4990 - top-5-accuracy: 0.9958

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 548ms/step - accuracy: 0.8412 - loss: 0.4976 - top-5-accuracy: 0.9956

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 547ms/step - accuracy: 0.8424 - loss: 0.4962 - top-5-accuracy: 0.9955

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.8436 - loss: 0.4952 - top-5-accuracy: 0.9953

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 547ms/step - accuracy: 0.8446 - loss: 0.4944 - top-5-accuracy: 0.9951

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 547ms/step - accuracy: 0.8455 - loss: 0.4939 - top-5-accuracy: 0.9950

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.8464 - loss: 0.4934 - top-5-accuracy: 0.9949

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.8471 - loss: 0.4928 - top-5-accuracy: 0.9948

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 546ms/step - accuracy: 0.8479 - loss: 0.4918 - top-5-accuracy: 0.9948

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 546ms/step - accuracy: 0.8485 - loss: 0.4910 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 546ms/step - accuracy: 0.8491 - loss: 0.4902 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 546ms/step - accuracy: 0.8496 - loss: 0.4896 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.8501 - loss: 0.4891 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 546ms/step - accuracy: 0.8507 - loss: 0.4884 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 546ms/step - accuracy: 0.8513 - loss: 0.4876 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.8519 - loss: 0.4868 - top-5-accuracy: 0.9947

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.8524 - loss: 0.4860 - top-5-accuracy: 0.9947 - val_accuracy: 0.7640 - val_loss: 0.5598 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 49/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 555ms/step - accuracy: 0.8125 - loss: 0.4499 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.7891 - loss: 0.4967 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 548ms/step - accuracy: 0.7830 - loss: 0.5083 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 548ms/step - accuracy: 0.7884 - loss: 0.5049 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.7920 - loss: 0.5022 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.7963 - loss: 0.4999 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.8011 - loss: 0.4957 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.8045 - loss: 0.4932 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 547ms/step - accuracy: 0.8081 - loss: 0.4891 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 547ms/step - accuracy: 0.8114 - loss: 0.4864 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.8135 - loss: 0.4862 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 547ms/step - accuracy: 0.8158 - loss: 0.4846 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 547ms/step - accuracy: 0.8170 - loss: 0.4846 - top-5-accuracy: 0.9998 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 547ms/step - accuracy: 0.8185 - loss: 0.4840 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 547ms/step - accuracy: 0.8200 - loss: 0.4827 - top-5-accuracy: 0.9996

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 547ms/step - accuracy: 0.8215 - loss: 0.4812 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 547ms/step - accuracy: 0.8228 - loss: 0.4802 - top-5-accuracy: 0.9993

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.8241 - loss: 0.4792 - top-5-accuracy: 0.9991

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.8254 - loss: 0.4776 - top-5-accuracy: 0.9990

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.8266 - loss: 0.4762 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.8278 - loss: 0.4748 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.8286 - loss: 0.4738 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 547ms/step - accuracy: 0.8296 - loss: 0.4724 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.8306 - loss: 0.4711 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 541ms/step - accuracy: 0.8314 - loss: 0.4703 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 538ms/step - accuracy: 0.8321 - loss: 0.4697 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 537ms/step - accuracy: 0.8329 - loss: 0.4690 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 539ms/step - accuracy: 0.8338 - loss: 0.4681 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 539ms/step - accuracy: 0.8346 - loss: 0.4673 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 539ms/step - accuracy: 0.8354 - loss: 0.4665 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 529ms/step - accuracy: 0.8362 - loss: 0.4656 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 571ms/step - accuracy: 0.8369 - loss: 0.4647 - top-5-accuracy: 0.9979 - val_accuracy: 0.6770 - val_loss: 0.7612 - val_top-5-accuracy: 0.9752


<div class="k-default-codeblock">
```
Epoch 50/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 555ms/step - accuracy: 0.8125 - loss: 0.6015 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 540ms/step - accuracy: 0.8125 - loss: 0.5859 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 541ms/step - accuracy: 0.8160 - loss: 0.5824 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 543ms/step - accuracy: 0.8190 - loss: 0.5680 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.8215 - loss: 0.5525 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.8260 - loss: 0.5348 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.8311 - loss: 0.5197 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.8337 - loss: 0.5107 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8352 - loss: 0.5034 - top-5-accuracy: 0.9992

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8367 - loss: 0.4977 - top-5-accuracy: 0.9989

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.8376 - loss: 0.4938 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.8381 - loss: 0.4911 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8387 - loss: 0.4887 - top-5-accuracy: 0.9986 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8392 - loss: 0.4865 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.8402 - loss: 0.4841 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8408 - loss: 0.4827 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8411 - loss: 0.4823 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.8413 - loss: 0.4822 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.8418 - loss: 0.4817 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.8423 - loss: 0.4811 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8429 - loss: 0.4805 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8434 - loss: 0.4801 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 544ms/step - accuracy: 0.8438 - loss: 0.4794 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8445 - loss: 0.4784 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8453 - loss: 0.4771 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8459 - loss: 0.4761 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8466 - loss: 0.4751 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8473 - loss: 0.4740 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8480 - loss: 0.4727 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8488 - loss: 0.4713 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.8494 - loss: 0.4704 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8500 - loss: 0.4695 - top-5-accuracy: 0.9978 - val_accuracy: 0.8012 - val_loss: 0.5141 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 51/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  18s 627ms/step - accuracy: 0.9375 - loss: 0.3551 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 608ms/step - accuracy: 0.9297 - loss: 0.3362 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 610ms/step - accuracy: 0.9288 - loss: 0.3265 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  16s 610ms/step - accuracy: 0.9193 - loss: 0.3370 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  15s 612ms/step - accuracy: 0.9129 - loss: 0.3463 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  15s 613ms/step - accuracy: 0.9109 - loss: 0.3493 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  14s 613ms/step - accuracy: 0.9096 - loss: 0.3517 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  14s 613ms/step - accuracy: 0.9082 - loss: 0.3532 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  13s 613ms/step - accuracy: 0.9080 - loss: 0.3527 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  12s 605ms/step - accuracy: 0.9085 - loss: 0.3512 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 600ms/step - accuracy: 0.9093 - loss: 0.3502 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 595ms/step - accuracy: 0.9095 - loss: 0.3499 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 590ms/step - accuracy: 0.9094 - loss: 0.3508 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 587ms/step - accuracy: 0.9093 - loss: 0.3513 - top-5-accuracy: 1.0000 

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 584ms/step - accuracy: 0.9090 - loss: 0.3522 - top-5-accuracy: 0.9999

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 584ms/step - accuracy: 0.9086 - loss: 0.3529 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 580ms/step - accuracy: 0.9083 - loss: 0.3535 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 578ms/step - accuracy: 0.9083 - loss: 0.3540 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 575ms/step - accuracy: 0.9079 - loss: 0.3547 - top-5-accuracy: 0.9993

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 574ms/step - accuracy: 0.9073 - loss: 0.3556 - top-5-accuracy: 0.9992

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 572ms/step - accuracy: 0.9068 - loss: 0.3566 - top-5-accuracy: 0.9990

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 571ms/step - accuracy: 0.9064 - loss: 0.3573 - top-5-accuracy: 0.9989

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 570ms/step - accuracy: 0.9061 - loss: 0.3576 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 569ms/step - accuracy: 0.9058 - loss: 0.3580 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 568ms/step - accuracy: 0.9056 - loss: 0.3583 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 567ms/step - accuracy: 0.9052 - loss: 0.3592 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 567ms/step - accuracy: 0.9049 - loss: 0.3599 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 566ms/step - accuracy: 0.9046 - loss: 0.3604 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 565ms/step - accuracy: 0.9043 - loss: 0.3609 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 564ms/step - accuracy: 0.9040 - loss: 0.3613 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 553ms/step - accuracy: 0.9038 - loss: 0.3620 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 19s 596ms/step - accuracy: 0.9035 - loss: 0.3626 - top-5-accuracy: 0.9982 - val_accuracy: 0.7888 - val_loss: 0.6614 - val_top-5-accuracy: 0.9689


<div class="k-default-codeblock">
```
Epoch 52/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 553ms/step - accuracy: 0.9688 - loss: 0.2355 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.9297 - loss: 0.2832 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.8941 - loss: 0.3329 - top-5-accuracy: 0.9965

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.8757 - loss: 0.3556 - top-5-accuracy: 0.9954

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 543ms/step - accuracy: 0.8668 - loss: 0.3693 - top-5-accuracy: 0.9939

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 542ms/step - accuracy: 0.8638 - loss: 0.3741 - top-5-accuracy: 0.9931

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 543ms/step - accuracy: 0.8609 - loss: 0.3796 - top-5-accuracy: 0.9928

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 543ms/step - accuracy: 0.8593 - loss: 0.3828 - top-5-accuracy: 0.9928

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.8595 - loss: 0.3833 - top-5-accuracy: 0.9928

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.8601 - loss: 0.3832 - top-5-accuracy: 0.9929

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.8599 - loss: 0.3852 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.8603 - loss: 0.3866 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8605 - loss: 0.3875 - top-5-accuracy: 0.9929 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 544ms/step - accuracy: 0.8612 - loss: 0.3873 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.8624 - loss: 0.3866 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8639 - loss: 0.3858 - top-5-accuracy: 0.9931

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8652 - loss: 0.3856 - top-5-accuracy: 0.9930

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 544ms/step - accuracy: 0.8661 - loss: 0.3863 - top-5-accuracy: 0.9929

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 544ms/step - accuracy: 0.8666 - loss: 0.3874 - top-5-accuracy: 0.9927

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 544ms/step - accuracy: 0.8673 - loss: 0.3882 - top-5-accuracy: 0.9926

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8676 - loss: 0.3890 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8682 - loss: 0.3894 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8687 - loss: 0.3899 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8693 - loss: 0.3902 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8699 - loss: 0.3906 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8706 - loss: 0.3906 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8713 - loss: 0.3903 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8722 - loss: 0.3899 - top-5-accuracy: 0.9925

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8731 - loss: 0.3892 - top-5-accuracy: 0.9926

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8738 - loss: 0.3887 - top-5-accuracy: 0.9926

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.8746 - loss: 0.3880 - top-5-accuracy: 0.9926

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8753 - loss: 0.3874 - top-5-accuracy: 0.9927 - val_accuracy: 0.8137 - val_loss: 0.5115 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 53/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 557ms/step - accuracy: 0.8750 - loss: 0.2998 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 543ms/step - accuracy: 0.9062 - loss: 0.2730 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 545ms/step - accuracy: 0.8993 - loss: 0.2896 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 546ms/step - accuracy: 0.8932 - loss: 0.3078 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 545ms/step - accuracy: 0.8883 - loss: 0.3175 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.8878 - loss: 0.3183 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.8873 - loss: 0.3234 - top-5-accuracy: 0.9994

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.8862 - loss: 0.3263 - top-5-accuracy: 0.9990

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8861 - loss: 0.3273 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.8869 - loss: 0.3268 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.8871 - loss: 0.3264 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.8874 - loss: 0.3265 - top-5-accuracy: 0.9983

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8872 - loss: 0.3276 - top-5-accuracy: 0.9982 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8874 - loss: 0.3283 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.8879 - loss: 0.3288 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8883 - loss: 0.3291 - top-5-accuracy: 0.9982

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8886 - loss: 0.3297 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.8889 - loss: 0.3307 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.8893 - loss: 0.3313 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.8898 - loss: 0.3316 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8905 - loss: 0.3316 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8912 - loss: 0.3316 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8918 - loss: 0.3314 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8923 - loss: 0.3313 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8927 - loss: 0.3312 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8931 - loss: 0.3311 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8935 - loss: 0.3310 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8938 - loss: 0.3309 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8941 - loss: 0.3309 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8944 - loss: 0.3308 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.8946 - loss: 0.3307 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 578ms/step - accuracy: 0.8948 - loss: 0.3305 - top-5-accuracy: 0.9978 - val_accuracy: 0.8385 - val_loss: 0.4534 - val_top-5-accuracy: 0.9938


<div class="k-default-codeblock">
```
Epoch 54/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 596ms/step - accuracy: 0.9375 - loss: 0.2209 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 522ms/step - accuracy: 0.9297 - loss: 0.2277 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  14s 532ms/step - accuracy: 0.9219 - loss: 0.2477 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 539ms/step - accuracy: 0.9141 - loss: 0.2622 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 542ms/step - accuracy: 0.9100 - loss: 0.2705 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.9042 - loss: 0.2882 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.9006 - loss: 0.2993 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.8989 - loss: 0.3053 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8959 - loss: 0.3125 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8935 - loss: 0.3194 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.8926 - loss: 0.3237 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.8922 - loss: 0.3276 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.8920 - loss: 0.3305 - top-5-accuracy: 1.0000 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8922 - loss: 0.3324 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.8926 - loss: 0.3344 - top-5-accuracy: 0.9999

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8931 - loss: 0.3358 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.8932 - loss: 0.3374 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.8931 - loss: 0.3393 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.8934 - loss: 0.3405 - top-5-accuracy: 0.9993

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.8938 - loss: 0.3413 - top-5-accuracy: 0.9992

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.8942 - loss: 0.3420 - top-5-accuracy: 0.9991

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8945 - loss: 0.3425 - top-5-accuracy: 0.9990

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.8949 - loss: 0.3428 - top-5-accuracy: 0.9989

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8954 - loss: 0.3430 - top-5-accuracy: 0.9989

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8959 - loss: 0.3431 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8965 - loss: 0.3429 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8971 - loss: 0.3426 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8977 - loss: 0.3422 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8982 - loss: 0.3417 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8987 - loss: 0.3413 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 535ms/step - accuracy: 0.8991 - loss: 0.3408 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8996 - loss: 0.3404 - top-5-accuracy: 0.9986 - val_accuracy: 0.7826 - val_loss: 0.5301 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 55/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 561ms/step - accuracy: 1.0000 - loss: 0.2476 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  16s 552ms/step - accuracy: 0.9844 - loss: 0.2611 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 551ms/step - accuracy: 0.9722 - loss: 0.2641 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 549ms/step - accuracy: 0.9674 - loss: 0.2631 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 548ms/step - accuracy: 0.9615 - loss: 0.2683 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.9592 - loss: 0.2684 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 547ms/step - accuracy: 0.9580 - loss: 0.2668 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.9574 - loss: 0.2644 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.9563 - loss: 0.2618 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.9557 - loss: 0.2596 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.9551 - loss: 0.2576 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.9541 - loss: 0.2568 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 546ms/step - accuracy: 0.9528 - loss: 0.2567 - top-5-accuracy: 1.0000 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 546ms/step - accuracy: 0.9515 - loss: 0.2568 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 546ms/step - accuracy: 0.9503 - loss: 0.2573 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 546ms/step - accuracy: 0.9493 - loss: 0.2581 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 545ms/step - accuracy: 0.9484 - loss: 0.2590 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.9476 - loss: 0.2598 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.9465 - loss: 0.2606 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.9457 - loss: 0.2613 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.9449 - loss: 0.2620 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 549ms/step - accuracy: 0.9443 - loss: 0.2625 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 549ms/step - accuracy: 0.9435 - loss: 0.2630 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 549ms/step - accuracy: 0.9429 - loss: 0.2635 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 552ms/step - accuracy: 0.9422 - loss: 0.2639 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 553ms/step - accuracy: 0.9416 - loss: 0.2643 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 553ms/step - accuracy: 0.9411 - loss: 0.2646 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 554ms/step - accuracy: 0.9406 - loss: 0.2650 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 553ms/step - accuracy: 0.9400 - loss: 0.2654 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 553ms/step - accuracy: 0.9395 - loss: 0.2655 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 543ms/step - accuracy: 0.9391 - loss: 0.2655 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 589ms/step - accuracy: 0.9387 - loss: 0.2654 - top-5-accuracy: 1.0000 - val_accuracy: 0.8075 - val_loss: 0.5284 - val_top-5-accuracy: 0.9876


<div class="k-default-codeblock">
```
Epoch 56/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  19s 646ms/step - accuracy: 0.8438 - loss: 0.3685 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 517ms/step - accuracy: 0.8750 - loss: 0.3146 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  14s 532ms/step - accuracy: 0.8924 - loss: 0.2991 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 539ms/step - accuracy: 0.8978 - loss: 0.2916 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 540ms/step - accuracy: 0.8995 - loss: 0.2900 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 541ms/step - accuracy: 0.9023 - loss: 0.2895 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  12s 541ms/step - accuracy: 0.9035 - loss: 0.2906 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 542ms/step - accuracy: 0.9049 - loss: 0.2907 - top-5-accuracy: 0.9975

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 543ms/step - accuracy: 0.9062 - loss: 0.2894 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.9081 - loss: 0.2873 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.9097 - loss: 0.2855 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 543ms/step - accuracy: 0.9109 - loss: 0.2840 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 543ms/step - accuracy: 0.9119 - loss: 0.2834 - top-5-accuracy: 0.9974 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 543ms/step - accuracy: 0.9127 - loss: 0.2826 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 544ms/step - accuracy: 0.9134 - loss: 0.2824 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 543ms/step - accuracy: 0.9141 - loss: 0.2824 - top-5-accuracy: 0.9975

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 544ms/step - accuracy: 0.9147 - loss: 0.2822 - top-5-accuracy: 0.9975

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 545ms/step - accuracy: 0.9152 - loss: 0.2823 - top-5-accuracy: 0.9975

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 545ms/step - accuracy: 0.9157 - loss: 0.2824 - top-5-accuracy: 0.9976

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  5s 545ms/step - accuracy: 0.9160 - loss: 0.2825 - top-5-accuracy: 0.9976

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 545ms/step - accuracy: 0.9162 - loss: 0.2829 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.9164 - loss: 0.2829 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 545ms/step - accuracy: 0.9166 - loss: 0.2831 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 544ms/step - accuracy: 0.9165 - loss: 0.2836 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.9161 - loss: 0.2845 - top-5-accuracy: 0.9978

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.9158 - loss: 0.2851 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 544ms/step - accuracy: 0.9156 - loss: 0.2856 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.9154 - loss: 0.2861 - top-5-accuracy: 0.9979

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 544ms/step - accuracy: 0.9151 - loss: 0.2869 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 544ms/step - accuracy: 0.9148 - loss: 0.2876 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.9146 - loss: 0.2882 - top-5-accuracy: 0.9980

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.9144 - loss: 0.2887 - top-5-accuracy: 0.9981 - val_accuracy: 0.7205 - val_loss: 0.6698 - val_top-5-accuracy: 0.9814


<div class="k-default-codeblock">
```
Epoch 57/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 558ms/step - accuracy: 0.8438 - loss: 0.3904 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 536ms/step - accuracy: 0.8594 - loss: 0.4059 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 544ms/step - accuracy: 0.8576 - loss: 0.4145 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.8620 - loss: 0.4029 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.8658 - loss: 0.3899 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.8648 - loss: 0.3871 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.8662 - loss: 0.3825 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.8668 - loss: 0.3810 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  11s 544ms/step - accuracy: 0.8685 - loss: 0.3782 - top-5-accuracy: 0.9992

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 545ms/step - accuracy: 0.8698 - loss: 0.3755 - top-5-accuracy: 0.9989

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 544ms/step - accuracy: 0.8708 - loss: 0.3741 - top-5-accuracy: 0.9988

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 545ms/step - accuracy: 0.8707 - loss: 0.3750 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8710 - loss: 0.3755 - top-5-accuracy: 0.9986 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.8715 - loss: 0.3755 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.8718 - loss: 0.3758 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 545ms/step - accuracy: 0.8723 - loss: 0.3758 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 546ms/step - accuracy: 0.8729 - loss: 0.3760 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 546ms/step - accuracy: 0.8735 - loss: 0.3758 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.8740 - loss: 0.3754 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 546ms/step - accuracy: 0.8747 - loss: 0.3746 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 546ms/step - accuracy: 0.8754 - loss: 0.3736 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.8762 - loss: 0.3722 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 546ms/step - accuracy: 0.8770 - loss: 0.3710 - top-5-accuracy: 0.9984

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 545ms/step - accuracy: 0.8779 - loss: 0.3696 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 545ms/step - accuracy: 0.8788 - loss: 0.3682 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 545ms/step - accuracy: 0.8797 - loss: 0.3667 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 545ms/step - accuracy: 0.8807 - loss: 0.3651 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8816 - loss: 0.3636 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 545ms/step - accuracy: 0.8824 - loss: 0.3622 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 545ms/step - accuracy: 0.8832 - loss: 0.3608 - top-5-accuracy: 0.9985

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 534ms/step - accuracy: 0.8839 - loss: 0.3593 - top-5-accuracy: 0.9986

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 18s 577ms/step - accuracy: 0.8846 - loss: 0.3579 - top-5-accuracy: 0.9986 - val_accuracy: 0.8509 - val_loss: 0.4617 - val_top-5-accuracy: 0.9938


<div class="k-default-codeblock">
```
Epoch 58/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  16s 557ms/step - accuracy: 0.9688 - loss: 0.1670 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.9766 - loss: 0.1665 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 547ms/step - accuracy: 0.9774 - loss: 0.1742 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.9792 - loss: 0.1744 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 544ms/step - accuracy: 0.9746 - loss: 0.1886 - top-5-accuracy: 0.9987

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 544ms/step - accuracy: 0.9727 - loss: 0.1941 - top-5-accuracy: 0.9981

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.9715 - loss: 0.1989 - top-5-accuracy: 0.9977

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.9712 - loss: 0.2022 - top-5-accuracy: 0.9975

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 558ms/step - accuracy: 0.9709 - loss: 0.2042 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 556ms/step - accuracy: 0.9707 - loss: 0.2060 - top-5-accuracy: 0.9974

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  11s 559ms/step - accuracy: 0.9703 - loss: 0.2078 - top-5-accuracy: 0.9973

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 565ms/step - accuracy: 0.9688 - loss: 0.2106 - top-5-accuracy: 0.9971

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  10s 563ms/step - accuracy: 0.9677 - loss: 0.2130 - top-5-accuracy: 0.9970

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 565ms/step - accuracy: 0.9665 - loss: 0.2149 - top-5-accuracy: 0.9969 

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 563ms/step - accuracy: 0.9653 - loss: 0.2168 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 563ms/step - accuracy: 0.9643 - loss: 0.2185 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 565ms/step - accuracy: 0.9635 - loss: 0.2198 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 565ms/step - accuracy: 0.9627 - loss: 0.2211 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 567ms/step - accuracy: 0.9621 - loss: 0.2220 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 565ms/step - accuracy: 0.9615 - loss: 0.2227 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 564ms/step - accuracy: 0.9609 - loss: 0.2233 - top-5-accuracy: 0.9967

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 564ms/step - accuracy: 0.9602 - loss: 0.2241 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 563ms/step - accuracy: 0.9596 - loss: 0.2247 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 564ms/step - accuracy: 0.9590 - loss: 0.2250 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 563ms/step - accuracy: 0.9585 - loss: 0.2255 - top-5-accuracy: 0.9968

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 563ms/step - accuracy: 0.9580 - loss: 0.2258 - top-5-accuracy: 0.9969

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 564ms/step - accuracy: 0.9577 - loss: 0.2259 - top-5-accuracy: 0.9969

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 566ms/step - accuracy: 0.9573 - loss: 0.2260 - top-5-accuracy: 0.9969

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 565ms/step - accuracy: 0.9571 - loss: 0.2260 - top-5-accuracy: 0.9970

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 565ms/step - accuracy: 0.9568 - loss: 0.2260 - top-5-accuracy: 0.9970

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 554ms/step - accuracy: 0.9565 - loss: 0.2262 - top-5-accuracy: 0.9970

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 19s 599ms/step - accuracy: 0.9562 - loss: 0.2265 - top-5-accuracy: 0.9971 - val_accuracy: 0.8199 - val_loss: 0.4840 - val_top-5-accuracy: 1.0000


<div class="k-default-codeblock">
```
Epoch 59/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  17s 577ms/step - accuracy: 1.0000 - loss: 0.1302 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 550ms/step - accuracy: 0.9922 - loss: 0.1269 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  15s 551ms/step - accuracy: 0.9878 - loss: 0.1294 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.9831 - loss: 0.1452 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  14s 547ms/step - accuracy: 0.9790 - loss: 0.1563 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  13s 546ms/step - accuracy: 0.9764 - loss: 0.1642 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  13s 545ms/step - accuracy: 0.9747 - loss: 0.1689 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 545ms/step - accuracy: 0.9729 - loss: 0.1744 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  12s 546ms/step - accuracy: 0.9717 - loss: 0.1787 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  11s 546ms/step - accuracy: 0.9708 - loss: 0.1816 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.9703 - loss: 0.1832 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  10s 546ms/step - accuracy: 0.9700 - loss: 0.1845 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  9s 545ms/step - accuracy: 0.9693 - loss: 0.1865 - top-5-accuracy: 1.0000 

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  9s 545ms/step - accuracy: 0.9690 - loss: 0.1881 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  8s 545ms/step - accuracy: 0.9687 - loss: 0.1893 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 551ms/step - accuracy: 0.9684 - loss: 0.1905 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  7s 554ms/step - accuracy: 0.9682 - loss: 0.1915 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  7s 553ms/step - accuracy: 0.9679 - loss: 0.1926 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 555ms/step - accuracy: 0.9675 - loss: 0.1938 - top-5-accuracy: 0.9999

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 554ms/step - accuracy: 0.9672 - loss: 0.1948 - top-5-accuracy: 0.9998

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  5s 560ms/step - accuracy: 0.9669 - loss: 0.1957 - top-5-accuracy: 0.9998

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 570ms/step - accuracy: 0.9667 - loss: 0.1965 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 571ms/step - accuracy: 0.9665 - loss: 0.1970 - top-5-accuracy: 0.9997

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  3s 568ms/step - accuracy: 0.9663 - loss: 0.1975 - top-5-accuracy: 0.9996

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 569ms/step - accuracy: 0.9661 - loss: 0.1978 - top-5-accuracy: 0.9996

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  2s 569ms/step - accuracy: 0.9660 - loss: 0.1981 - top-5-accuracy: 0.9996

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 573ms/step - accuracy: 0.9659 - loss: 0.1982 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 578ms/step - accuracy: 0.9659 - loss: 0.1982 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 581ms/step - accuracy: 0.9659 - loss: 0.1981 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 584ms/step - accuracy: 0.9659 - loss: 0.1980 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 576ms/step - accuracy: 0.9659 - loss: 0.1977 - top-5-accuracy: 0.9995

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 19s 621ms/step - accuracy: 0.9658 - loss: 0.1975 - top-5-accuracy: 0.9994 - val_accuracy: 0.8385 - val_loss: 0.4939 - val_top-5-accuracy: 1.0000


<div class="k-default-codeblock">
```
Epoch 60/60

```
</div>
    
  1/31 [37m━━━━━━━━━━━━━━━━━━━━  24s 808ms/step - accuracy: 0.9688 - loss: 0.1658 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/31 ━[37m━━━━━━━━━━━━━━━━━━━  17s 620ms/step - accuracy: 0.9766 - loss: 0.1586 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  3/31 ━[37m━━━━━━━━━━━━━━━━━━━  19s 679ms/step - accuracy: 0.9740 - loss: 0.1568 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  4/31 ━━[37m━━━━━━━━━━━━━━━━━━  18s 703ms/step - accuracy: 0.9707 - loss: 0.1585 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  5/31 ━━━[37m━━━━━━━━━━━━━━━━━  18s 710ms/step - accuracy: 0.9703 - loss: 0.1579 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  6/31 ━━━[37m━━━━━━━━━━━━━━━━━  17s 709ms/step - accuracy: 0.9709 - loss: 0.1561 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  7/31 ━━━━[37m━━━━━━━━━━━━━━━━  16s 673ms/step - accuracy: 0.9712 - loss: 0.1547 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  8/31 ━━━━━[37m━━━━━━━━━━━━━━━  15s 656ms/step - accuracy: 0.9704 - loss: 0.1546 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  9/31 ━━━━━[37m━━━━━━━━━━━━━━━  14s 646ms/step - accuracy: 0.9703 - loss: 0.1538 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 10/31 ━━━━━━[37m━━━━━━━━━━━━━━  13s 639ms/step - accuracy: 0.9701 - loss: 0.1537 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 11/31 ━━━━━━━[37m━━━━━━━━━━━━━  12s 641ms/step - accuracy: 0.9697 - loss: 0.1544 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 12/31 ━━━━━━━[37m━━━━━━━━━━━━━  12s 638ms/step - accuracy: 0.9694 - loss: 0.1549 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 13/31 ━━━━━━━━[37m━━━━━━━━━━━━  11s 631ms/step - accuracy: 0.9688 - loss: 0.1558 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 14/31 ━━━━━━━━━[37m━━━━━━━━━━━  10s 631ms/step - accuracy: 0.9683 - loss: 0.1567 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 15/31 ━━━━━━━━━[37m━━━━━━━━━━━  10s 633ms/step - accuracy: 0.9675 - loss: 0.1583 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 16/31 ━━━━━━━━━━[37m━━━━━━━━━━  9s 630ms/step - accuracy: 0.9670 - loss: 0.1598 - top-5-accuracy: 1.0000 

<div class="k-default-codeblock">
```

```
</div>
 17/31 ━━━━━━━━━━[37m━━━━━━━━━━  8s 628ms/step - accuracy: 0.9666 - loss: 0.1609 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 18/31 ━━━━━━━━━━━[37m━━━━━━━━━  8s 634ms/step - accuracy: 0.9661 - loss: 0.1618 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 19/31 ━━━━━━━━━━━━[37m━━━━━━━━  7s 632ms/step - accuracy: 0.9657 - loss: 0.1626 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 20/31 ━━━━━━━━━━━━[37m━━━━━━━━  6s 631ms/step - accuracy: 0.9653 - loss: 0.1639 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 21/31 ━━━━━━━━━━━━━[37m━━━━━━━  6s 627ms/step - accuracy: 0.9650 - loss: 0.1650 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 22/31 ━━━━━━━━━━━━━━[37m━━━━━━  5s 623ms/step - accuracy: 0.9648 - loss: 0.1659 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 23/31 ━━━━━━━━━━━━━━[37m━━━━━━  4s 622ms/step - accuracy: 0.9646 - loss: 0.1666 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 24/31 ━━━━━━━━━━━━━━━[37m━━━━━  4s 619ms/step - accuracy: 0.9644 - loss: 0.1675 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 25/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 614ms/step - accuracy: 0.9642 - loss: 0.1684 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 26/31 ━━━━━━━━━━━━━━━━[37m━━━━  3s 613ms/step - accuracy: 0.9641 - loss: 0.1691 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 27/31 ━━━━━━━━━━━━━━━━━[37m━━━  2s 609ms/step - accuracy: 0.9640 - loss: 0.1697 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 28/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 613ms/step - accuracy: 0.9638 - loss: 0.1703 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 29/31 ━━━━━━━━━━━━━━━━━━[37m━━  1s 620ms/step - accuracy: 0.9636 - loss: 0.1708 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 30/31 ━━━━━━━━━━━━━━━━━━━[37m━  0s 620ms/step - accuracy: 0.9634 - loss: 0.1714 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 0s 607ms/step - accuracy: 0.9632 - loss: 0.1720 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
 31/31 ━━━━━━━━━━━━━━━━━━━━ 20s 651ms/step - accuracy: 0.9630 - loss: 0.1725 - top-5-accuracy: 1.0000 - val_accuracy: 0.8012 - val_loss: 0.5563 - val_top-5-accuracy: 0.9814


    
  1/20 ━[37m━━━━━━━━━━━━━━━━━━━  5s 282ms/step - accuracy: 0.8125 - loss: 0.6850 - top-5-accuracy: 1.0000

<div class="k-default-codeblock">
```

```
</div>
  2/20 ━━[37m━━━━━━━━━━━━━━━━━━  4s 258ms/step - accuracy: 0.7656 - loss: 0.9808 - top-5-accuracy: 0.9844

<div class="k-default-codeblock">
```

```
</div>
  3/20 ━━━[37m━━━━━━━━━━━━━━━━━  4s 257ms/step - accuracy: 0.7396 - loss: 1.0973 - top-5-accuracy: 0.9757

<div class="k-default-codeblock">
```

```
</div>
  4/20 ━━━━[37m━━━━━━━━━━━━━━━━  4s 257ms/step - accuracy: 0.7266 - loss: 1.1479 - top-5-accuracy: 0.9701

<div class="k-default-codeblock">
```

```
</div>
  5/20 ━━━━━[37m━━━━━━━━━━━━━━━  3s 265ms/step - accuracy: 0.7212 - loss: 1.1652 - top-5-accuracy: 0.9660

<div class="k-default-codeblock">
```

```
</div>
  6/20 ━━━━━━[37m━━━━━━━━━━━━━━  3s 266ms/step - accuracy: 0.7148 - loss: 1.1783 - top-5-accuracy: 0.9639

<div class="k-default-codeblock">
```

```
</div>
  7/20 ━━━━━━━[37m━━━━━━━━━━━━━  3s 269ms/step - accuracy: 0.7115 - loss: 1.1756 - top-5-accuracy: 0.9633

<div class="k-default-codeblock">
```

```
</div>
  8/20 ━━━━━━━━[37m━━━━━━━━━━━━  3s 263ms/step - accuracy: 0.7070 - loss: 1.1743 - top-5-accuracy: 0.9625

<div class="k-default-codeblock">
```

```
</div>
  9/20 ━━━━━━━━━[37m━━━━━━━━━━━  2s 258ms/step - accuracy: 0.7045 - loss: 1.1713 - top-5-accuracy: 0.9624

<div class="k-default-codeblock">
```

```
</div>
 10/20 ━━━━━━━━━━[37m━━━━━━━━━━  2s 263ms/step - accuracy: 0.7028 - loss: 1.1675 - top-5-accuracy: 0.9624

<div class="k-default-codeblock">
```

```
</div>
 11/20 ━━━━━━━━━━━[37m━━━━━━━━━  2s 261ms/step - accuracy: 0.7009 - loss: 1.1624 - top-5-accuracy: 0.9628

<div class="k-default-codeblock">
```

```
</div>
 12/20 ━━━━━━━━━━━━[37m━━━━━━━━  2s 257ms/step - accuracy: 0.6987 - loss: 1.1610 - top-5-accuracy: 0.9626

<div class="k-default-codeblock">
```

```
</div>
 13/20 ━━━━━━━━━━━━━[37m━━━━━━━  1s 280ms/step - accuracy: 0.6965 - loss: 1.1605 - top-5-accuracy: 0.9623

<div class="k-default-codeblock">
```

```
</div>
 14/20 ━━━━━━━━━━━━━━[37m━━━━━━  1s 281ms/step - accuracy: 0.6946 - loss: 1.1605 - top-5-accuracy: 0.9622

<div class="k-default-codeblock">
```

```
</div>
 15/20 ━━━━━━━━━━━━━━━[37m━━━━━  1s 284ms/step - accuracy: 0.6927 - loss: 1.1629 - top-5-accuracy: 0.9618

<div class="k-default-codeblock">
```

```
</div>
 16/20 ━━━━━━━━━━━━━━━━[37m━━━━  1s 283ms/step - accuracy: 0.6919 - loss: 1.1622 - top-5-accuracy: 0.9616

<div class="k-default-codeblock">
```

```
</div>
 17/20 ━━━━━━━━━━━━━━━━━[37m━━━  0s 282ms/step - accuracy: 0.6909 - loss: 1.1645 - top-5-accuracy: 0.9614

<div class="k-default-codeblock">
```

```
</div>
 18/20 ━━━━━━━━━━━━━━━━━━[37m━━  0s 292ms/step - accuracy: 0.6892 - loss: 1.1689 - top-5-accuracy: 0.9609

<div class="k-default-codeblock">
```

```
</div>
 19/20 ━━━━━━━━━━━━━━━━━━━[37m━  0s 304ms/step - accuracy: 0.6880 - loss: 1.1715 - top-5-accuracy: 0.9606

<div class="k-default-codeblock">
```

```
</div>
 20/20 ━━━━━━━━━━━━━━━━━━━━ 6s 291ms/step - accuracy: 0.6858 - loss: 1.1736 - top-5-accuracy: 0.9602


<div class="k-default-codeblock">
```
Test accuracy: 66.56%
Test top 5 accuracy: 95.57%

```
</div>
---
## Inference


```python
NUM_SAMPLES_VIZ = 25
testsamples, labels = next(iter(testloader))
testsamples, labels = testsamples[:NUM_SAMPLES_VIZ], labels[:NUM_SAMPLES_VIZ]

ground_truths = []
preds = []
videos = []

for i, (testsample, label) in enumerate(zip(testsamples, labels)):
    # Generate gif
    testsample = ops.reshape(testsample, (-1, 28, 28))
    with io.BytesIO() as gif:
        imageio.mimsave(gif, (testsample.numpy() * 255).astype("uint8"), "GIF", fps=5)
        videos.append(gif.getvalue())

    # Get model prediction
    output = model.predict(ops.expand_dims(testsample, axis=0))[0]
    pred = np.argmax(output, axis=0)

    ground_truths.append(label.numpy().astype("int"))
    preds.append(pred)


def make_box_for_grid(image_widget, fit):
    """Make a VBox to hold caption/image for demonstrating option_fit values.

    Source: https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Styling.html
    """
    # Make the caption
    if fit is not None:
        fit_str = "'{}'".format(fit)
    else:
        fit_str = str(fit)

    h = ipywidgets.HTML(value="" + str(fit_str) + "")

    # Make the green box with the image widget inside it
    boxb = ipywidgets.widgets.Box()
    boxb.children = [image_widget]

    # Compose into a vertical box
    vb = ipywidgets.widgets.VBox()
    vb.layout.align_items = "center"
    vb.children = [h, boxb]
    return vb


boxes = []
for i in range(NUM_SAMPLES_VIZ):
    ib = ipywidgets.widgets.Image(value=videos[i], width=100, height=100)
    true_class = info["label"][str(ground_truths[i])]
    pred_class = info["label"][str(preds[i])]
    caption = f"T: {true_class} | P: {pred_class}"

    boxes.append(make_box_for_grid(ib, caption))

ipywidgets.widgets.GridBox(
    boxes, layout=ipywidgets.widgets.Layout(grid_template_columns="repeat(5, 200px)")
)
```

    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 10s/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 10s 10s/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 45ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 48ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 60ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 62ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 48ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 45ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 43ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 44ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 45ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 44ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 79ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 83ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 83ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 86ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 95ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 99ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 83ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 85ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 58ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 60ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 52ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 54ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 49ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 51ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 52ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 97ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 104ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 45ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 44ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 48ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 46ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 47ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 50ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 51ms/step


    
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 50ms/step

<div class="k-default-codeblock">
```

```
</div>
 1/1 ━━━━━━━━━━━━━━━━━━━━ 0s 52ms/step





<div class="k-default-codeblock">
```
GridBox(children=(VBox(children=(HTML(value="'T: pancreas | P: pancreas'"), Box(children=(Image(value=b'GIF89a…

```
</div>
---
## Final thoughts

With a vanilla implementation, we achieve ~79-80% Top-1 accuracy on the
test dataset.

The hyperparameters used in this tutorial were finalized by running a
hyperparameter search using
[W&B Sweeps](https://docs.wandb.ai/guides/sweeps).
You can find out our sweeps result
[here](https://wandb.ai/minimal-implementations/vivit/sweeps/66fp0lhz)
and our quick analysis of the results
[here](https://wandb.ai/minimal-implementations/vivit/reports/Hyperparameter-Tuning-Analysis--VmlldzoxNDEwNzcx).

For further improvement, you could look into the following:

- Using data augmentation for videos.
- Using a better regularization scheme for training.
- Apply different variants of the transformer model as in the paper.

We would like to thank [Anurag Arnab](https://anuragarnab.github.io/)
(first author of ViViT) for helpful discussion. We are grateful to
[Weights and Biases](https://wandb.ai/site) program for helping with
GPU credits.

You can use the trained model hosted on [Hugging Face Hub](https://huggingface.co/keras-io/video-vision-transformer)
and try the demo on [Hugging Face Spaces](https://huggingface.co/spaces/keras-io/video-vision-transformer-CT).
