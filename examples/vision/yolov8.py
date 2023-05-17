"""
Title: Efficient Object Detection with YOLOV8 and KerasCV
Author: [Gitesh Chawda](https://www.linkedin.com/in/gitesh-ch/)
Date created: 2023/05/15
Last modified: 2023/05/15
Description: Train custom YOLOV8 object detection model with KerasCV.
"""

"""
KerasCV is a deep learning library built on top of Keras, a popular deep learning
framework. KerasCV provides a set of tools and utilities for building and training deep
learning models for computer vision tasks, such as image classification, object
detection, and segmentation.

KerasCV includes pre-trained models for popular computer vision datasets, such as
ImageNet, COCO, and Pascal VOC, which can be used for transfer learning.KerasCV also
provides a range of visualization tools for inspecting the intermediate representations
learned by the model and for visualizing the results of object detection and segmentation
tasks.
"""

"""
If you're interested in learning about object detection using KerasCV, I highly suggest
taking a look at the guide created by lukewood. This resource, available at [OD With
KerasCV](https://keras.io/guides/keras_cv/object_detection_keras_cv/#object-detection-intr
oduction), provides a comprehensive overview of the fundamental concepts and techniques
required for building object detection models with KerasCV.
"""

"""shell
!!pip install --upgrade git+https://github.com/keras-team/keras-cv -q
"""

"""
# Setup
"""

import os
import glob
import numpy as np
from tqdm.auto import tqdm
import xml.etree.ElementTree as ET

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import optimizers

import keras_cv
from keras_cv import bounding_box
from keras_cv import visualization

"""
# Load Data
"""

"""

The Aquarium Dataset is a collection of 638 images obtained from two aquariums in the
United States: The Henry Doorly Zoo in Omaha (October 16, 2020) and the National Aquarium
in Baltimore (November 14, 2020). These images were curated and labeled for object
detection by the Roboflow team, with assistance from SageMaker Ground Truth. The dataset,
including both the images and annotations
"""

"""
The TensorFlow Datasets library provides a convenient way to download and use various
datasets, including the object dataset. This can be a great option for those who want to
quickly start working with the data without having to manually download and preprocess
it.

You can view various OD datasets here [Tensorflow
Datasets](https://www.tensorflow.org/datasets/catalog/overview#object_detection)

However, in this code example, we will demonstrate how to load the dataset from scratch
using TensorFlow's tf.data pipeline. This approach provides more flexibility and allows
you to customize the preprocessing steps as needed.

loading custom datasets that are not available in the TensorFlow Datasets library is one
of the main advantages of using the tf.data pipeline. This approach allows you to create
a custom data preprocessing pipeline tailored to the specific needs and requirements of
your dataset.
"""

"""shell
!unzip -q /content/drive/MyDrive/dataset.zip
"""

"""
# Hyperparameters
"""

SPLIT_RATIO = 0.2
BATCH_SIZE = 4
LEARNING_RATE = 1e-6
EPOCH = 5
MOMENTUM = 0.9
GLOBAL_CLIPNORM = 10.0

"""
In object detection tasks, it is important to know the specific class of each object that
the model detects in an image. To achieve this, a list of class names or labels is often
used to label the objects detected in an image.

A dictionary is created to map each class name to a unique numerical identifier. This
mapping is used to encode and decode the class labels during training and inference in
object detection tasks.
"""

class_ids = [
    "fish",
    "jellyfish",
    "penguin",
    "shark",
    "puffin",
    "stingray",
    "starfish",
]
class_mapping = dict(zip(range(len(class_ids)), class_ids))

# Path to images and annotations
path_images = "/content/JPEGImages/"
path_annot = "/content/Annotations/"

# Get all XML file paths in path_annot and sort them
xml_files = sorted(
    [
        os.path.join(path_annot, file_name)
        for file_name in os.listdir(path_annot)
        if file_name.endswith(".xml")
    ]
)

# Get all JPEG image file paths in path_images and sort them
jpg_files = sorted(
    [
        os.path.join(path_images, file_name)
        for file_name in os.listdir(path_images)
        if file_name.endswith(".jpg")
    ]
)

"""
Below function reads the xml file and finds the image name and path, and then iterates
over each object in the XML file to extract the bounding box coordinates and class labels
for each object.

The function returns three values: the image path, a list of bounding boxes (each
represented as a list of four floats: xmin, ymin, xmax, ymax), and a list of class IDs
(represented as integers) corresponding to each bounding box. The class IDs are obtained
by mapping the class labels to integer values using a dictionary called `class_mapping`.
"""


def parse_annotation(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    image_name = root.find("filename").text
    image_path = os.path.join(path_images, image_name)

    boxes = []
    classes = []
    for obj in root.iter("object"):
        cls = obj.find("name").text
        classes.append(cls)

        bbox = obj.find("bndbox")
        xmin = float(bbox.find("xmin").text)
        ymin = float(bbox.find("ymin").text)
        xmax = float(bbox.find("xmax").text)
        ymax = float(bbox.find("ymax").text)
        boxes.append([xmin, ymin, xmax, ymax])

    class_ids = [
        list(class_mapping.keys())[list(class_mapping.values()).index(cls)]
        for cls in classes
    ]
    return image_path, boxes, class_ids


image_paths = []
bbox = []
classes = []
for xml_file in tqdm(xml_files):
    image_path, boxes, class_ids = parse_annotation(xml_file)
    image_paths.append(image_path)
    bbox.append(boxes)
    classes.append(class_ids)

"""
Here we are using `tf.ragged.constant` to create ragged tensors from the bbox and classes
lists. A ragged tensor is a type of tensor that can handle varying lengths of data along
one or more dimensions. This is useful when dealing with data that has variable-length
sequences, such as text or time series data.

```python
classes = [[8, 8, 8, 8, 8], # 5 classes
 [12, 14, 14, 14],          # 4 clsses
 [1],                       # 1 class
 [7, 7],                    # 2 class
 ...]
```

```python
bbox = [[199.0, 19.0, 390.0, 401.0],
  [217.0, 15.0, 270.0, 157.0],
  [393.0, 18.0, 432.0, 162.0],
  [1.0, 15.0, 226.0, 276.0],
  [19.0, 95.0, 458.0, 443.0]],  #bbox 1 having 4 objects
 [[52.0, 117.0, 109.0, 177.0]], #bbox 2 having 1 object
 [[88.0, 87.0, 235.0, 322.0], [113.0, 117.0, 218.0, 471.0]], #bbox 2 having 2 objects
 ...]
```

In this case, the bbox and classes lists have different lengths for each image, depending
on the number of objects in the image and the corresponding bounding boxes and classes.
To handle this variability, ragged tensors are used instead of regular tensors.

Later, these ragged tensors are used to create a `tf.data.Dataset` using the
`from_tensor_slices` method. This method creates a dataset from the input tensors by
slicing them along the first dimension. By using ragged tensors, the dataset can handle
varying lengths of data for each image and provide a flexible input pipeline for further
processing.
"""

bbox = tf.ragged.constant(bbox)
classes = tf.ragged.constant(classes)
image_paths = tf.ragged.constant(image_paths)

data = tf.data.Dataset.from_tensor_slices((image_paths, classes, bbox))

"""
Splitting data in training and validation data
"""

# Determine the number of validation samples
num_val = int(len(xml_files) * SPLIT_RATIO)

# Split the dataset into train and validation sets
val_data = data.take(num_val)
train_data = data.skip(num_val)

"""
Let's see about data loading and bounding box formatting to get things going. Bounding
boxes in KerasCV have a predetermined format. To do this, you must bundle your bounding
boxes into a dictionary that complies with the requirements listed below:

```python
bounding_boxes = {
    # num_boxes may be a Ragged dimension
    'boxes': Tensor(shape=[batch, num_boxes, 4]),
    'classes': Tensor(shape=[batch, num_boxes])
}
```

The dictionary has two keys, `'boxes'` and `'classes'`, each of which maps to a
TensorFlow RaggedTensor or Tensor object. The 'boxes' Tensor has a shape of `[batch,
num_boxes, 4]`, where batch is the number of images in the batch and num_boxes is the
maximum number of bounding boxes in any image. The 4 represents the four values needed to
define a bounding box:  xmin, ymin, xmax, ymax.

The 'classes' Tensor has a shape of `[batch, num_boxes]`, where each element represents
the class label for the corresponding bounding box in the 'boxes' Tensor. The num_boxes
dimension may be ragged, which means that the number of boxes may vary across images in
the batch.

Final dict should be:
```python
{"images": images, "bounding_boxes": bounding_boxes}
```
"""


def load_image(image_path):
    image = tf.io.read_file(image_path)
    image = tf.image.decode_jpeg(image, channels=3)
    return image


def load_dataset(image_path, classes, bbox):
    # Read Image
    image = load_image(image_path)
    bounding_boxes = {
        "classes": tf.cast(classes, dtype=tf.float32),
        "boxes": bbox,
    }
    return {"images": tf.cast(image, tf.float32), "bounding_boxes": bounding_boxes}


"""
Here we create a layer that resizes images to 640x640 pixels, while maintaining the
original aspect ratio. The bounding boxes associated with the image are specified in the
`xyxy` format. If necessary, the resized image will be padded with zeros to maintain the
original aspect ratio.

Bounding Box Formats supported by KerasCV:
1.   CENTER_XYWH
2.   XYWH
3.   XYXY
4.   REL_XYXY

You can read more about KerasCV bounding box formats in
[docs](https://keras.io/api/keras_cv/bounding_box/formats/).

Also, you can convert one format to another using:

```python
boxes = keras_cv.bounding_box.convert_format(
        bounding_box,
        images=image,
        source="xyxy",  # Original Format
        target="xywh",  # Target Format (to which we want to convert)
    )
```

Conversion you can do using KerasCV:


1.   center_yxhw to xyxy
2.   center_xywh to xyxy
3.   xywh to xyxy
4.   xyxy to center_yxhw
5.   rel_xywh to xyxy
6.   xyxy to xywh
7.   xyxy to rel_xywh
8.   xyxy to center_xywh
9.   rel_xyxy to xyxy
10.  xyxy to_rel xyxy
11.  yxyx to xyxy
12.  rel_yxyx to xyxy
13.  xyxy to yxyx
14.  xyxy to rel_yxyx





"""

resizing = keras_cv.layers.Resizing(
    640, 640, bounding_box_format="xyxy", pad_to_aspect_ratio=True
)

"""
Creating Training Dataset 
"""

train_ds = train_data.map(load_dataset, num_parallel_calls=tf.data.AUTOTUNE)
train_ds = train_ds.shuffle(BATCH_SIZE * 4)
train_ds = train_ds.ragged_batch(BATCH_SIZE, drop_remainder=True)
train_ds = train_ds.map(resizing, num_parallel_calls=tf.data.AUTOTUNE)

"""
Creating Validation Dataset
"""

val_ds = val_data.map(load_dataset, num_parallel_calls=tf.data.AUTOTUNE)
val_ds = val_ds.shuffle(BATCH_SIZE * 4)
val_ds = val_ds.ragged_batch(BATCH_SIZE, drop_remainder=True)
val_ds = val_ds.map(resizing, num_parallel_calls=tf.data.AUTOTUNE)

"""
# Visualization
"""


def visualize_dataset(inputs, value_range, rows, cols, bounding_box_format):
    inputs = next(iter(inputs.take(1)))
    images, bounding_boxes = inputs["images"], inputs["bounding_boxes"]
    visualization.plot_bounding_box_gallery(
        images,
        value_range=value_range,
        rows=rows,
        cols=cols,
        y_true=bounding_boxes,
        scale=5,
        font_scale=0.7,
        bounding_box_format=bounding_box_format,
        class_mapping=class_mapping,
    )


visualize_dataset(
    train_ds, bounding_box_format="xyxy", value_range=(0, 255), rows=2, cols=2
)

visualize_dataset(
    val_ds, bounding_box_format="xyxy", value_range=(0, 255), rows=2, cols=2
)

"""
We need to extract the inputs from the preprocessing dictionary and get them ready to be
fed into the model. If we're using TPU, we need to make sure that the bounding box
Tensors are Dense rather than Ragged. If we're training on GPU, we don't need to make
this change and can skip the `bounding_box.to_dense()` call.
"""


def dict_to_tuple(inputs):
    return inputs["images"], bounding_box.to_dense(
        inputs["bounding_boxes"], max_boxes=32
    )


train_ds = train_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
train_ds = train_ds.prefetch(tf.data.AUTOTUNE)

val_ds = val_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
val_ds = val_ds.prefetch(tf.data.AUTOTUNE)

"""
# Creating Model
"""

"""
YOLOv8 is a cutting-edge YOLO model that is used for a variety of computer vision tasks,
such as object detection, image classification, and instance segmentation. Ultralytics,
the creators of YOLOv5, also developed YOLOv8, which incorporates many improvements and
changes in architecture and developer experience compared to its predecessor. YOLOv8 is
the latest state-of-the-art model that is highly regarded in the industry.
"""

"""
Below table compares the performance metrics of five different YOLOv8 models with
different sizes (measured in pixels): YOLOv8n, YOLOv8s, YOLOv8m, YOLOv8l, and YOLOv8x.
The metrics include mean average precision (mAP) values at different
intersection-over-union (IoU) thresholds for validation data, inference speed on CPU with
ONNX format and A100 TensorRT, number of parameters, and number of floating-point
operations (FLOPs) (both in millions and billions, respectively). As the size of the
model increases, the mAP, parameters, and FLOPs generally increase while the speed
decreases. YOLOv8x has the highest mAP, parameters, and FLOPs but also the slowest
inference speed, while YOLOv8n has the smallest size, fastest inference speed, and lowest
mAP, parameters, and FLOPs.

| Model                                                                                |
size<br><sup>(pixels) | mAP<sup>val<br>50-95 | Speed<br><sup>CPU ONNX<br>(ms) |
Speed<br><sup>A100 TensorRT<br>(ms) | params<br><sup>(M) | FLOPs<br><sup>(B) |
| ------------------------------------------------------------------------------------ |
--------------------- | -------------------- | ------------------------------ |
----------------------------------- | ------------------ | ----------------- |
| YOLOv8n | 640                   | 37.3                 | 80.4                          
| 0.99                                | 3.2                | 8.7               |
| YOLOv8s | 640                   | 44.9                 | 128.4                         
| 1.20                                | 11.2               | 28.6              |
| YOLOv8m | 640                   | 50.2                 | 234.7                         
| 1.83                                | 25.9               | 78.9              |
| YOLOv8l | 640                   | 52.9                 | 375.2                         
| 2.39                                | 43.7               | 165.2             |
| YOLOv8x | 640                   | 53.9                 | 479.1                         
| 3.53                                | 68.2               | 257.8             |
"""

"""
You can read more about YOLOV8 and its architecture in this [RoboFlow
Blog](https://blog.roboflow.com/whats-new-in-yolov8/)
"""

"""
First we will create a instance of backbone which will be used by our yolov8 detector
class. 

Backbones available in KerasCV:

1.   Without Weights:

    1.   yolo_v8_xs_backbone
    2.   yolo_v8_s_backbone
    3.   yolo_v8_m_backbone
    4.   yolo_v8_l_backbone
    5.   yolo_v8_xl_backbone

2. With Pre-trained coco weight:

    1.   yolo_v8_xs_backbone_coco
    2.   yolo_v8_s_backbone_coco
    2.   yolo_v8_m_backbone_coco
    2.   yolo_v8_l_backbone_coco
    2.   yolo_v8_xl_backbone_coco



"""

backbone = keras_cv.models.YOLOV8Backbone.from_preset(
    "yolo_v8_s_backbone"  # We will use yolov8 small backbone
)

"""
Next, let's build a YOLOV8 model using the `YOLOV8Detector`, which accepts a feature
extractor as the `backbone` argument, a `num_classes` argument that specifies the number
of object classes to detect based on the size of the `class_mapping` list, a
`bounding_box_format` argument that informs the model of the format of the bbox in the
dataset, and a Finally, the feature pyramid network (FPN) depth is specified by the
`fpn_depth` argument.

It is simple to build a YOLOV8 using any of the aforementioned backbones thanks to
KerasCV.

"""

yolo = keras_cv.models.YOLOV8Detector(
    num_classes=len(class_mapping),
    bounding_box_format="xyxy",
    backbone=backbone,
    fpn_depth=1,
)

"""
# Compile the Model
"""

"""
Loss used for YOLOV8


1. Classification Loss: This loss function calculates the discrepancy between anticipated
class probabilities and actual class probabilities. In this instance,
`binary_crossentropy`, a prominent solution for binary classification issues, is
utilised. We utilised binary crossentropy since each thing that is identified is either
classed as belonging to or not belonging to a certain object class (such as a person, a
car, etc.).

2. Box Loss:  `box_loss` is the loss function used to measure the difference between the
predicted bounding boxes and the ground truth. In this case, the Intersection over Union
(IoU) metric is used, which measures the overlap between predicted and ground truth
bounding boxes. Together, these loss functions help optimize the model for object
detection by minimizing the difference between the predicted and ground truth class
probabilities and bounding boxes.


"""

yolo.compile(
    optimizer="adam", classification_loss="binary_crossentropy", box_loss="iou"
)

"""
# Train the Model
"""

yolo.fit(
    train_ds.take(100),
    validation_data=val_ds.take(100),
    epochs=5,
)

"""
# Visualize Predictions
"""


def visualize_detections(model, dataset, bounding_box_format):
    images, y_true = next(iter(dataset.take(1)))
    y_pred = model.predict(images)
    y_pred = bounding_box.to_ragged(y_pred)
    visualization.plot_bounding_box_gallery(
        images,
        value_range=(0, 255),
        bounding_box_format=bounding_box_format,
        y_true=y_true,
        y_pred=y_pred,
        scale=4,
        rows=2,
        cols=2,
        show=True,
        font_scale=0.7,
        class_mapping=class_mapping,
    )


visualize_detections(yolo, dataset=val_ds, bounding_box_format="xyxy")
