"""
Title: The Distribution API for multi-backend Keras
Author: [Qianli Zhu](https://github.com/qlzh727)
Date created: 2023/11/07
Last modified: 2023/11/07
Description: Complete guide to the distribution API for multi-backend Keras.
Accelerator: GPU
"""

"""
## Setup
"""

import keras
from keras import distribution

"""
## Introduction

The Keras distribution API is a new API interface designed to facilitate 
distributed deep learning across a variety of backends like JAX, Tensorflow and
Pytorch. This innovative API introduces a suite of tools enabling data and model
parallelism, allowing for efficient scaling of deep learning models on multiple
accelerators and hosts. Whether leveraging the power of GPUs or TPUs, the API 
provides a streamlined approach to initializing distributed environments, 
defining device meshes, and orchestrating the layout of tensors across 
computational resources. Through classes like `DataParallel` and 
`ModelParallel`, it abstracts the complexity involved in parallel computation, 
making it accessible for developers to accelerate their machine learning 
workflows.

"""

"""
## How it works

The Keras distribution API provides a global programming model that allows 
developers to compose applications that operate on Tensors globally while 
managing the distribution across devices internally. The API leverage the 
underlying framework to distribute the program and tensors according to the 
sharding directives through a procedure called Single program, multiple data 
(SPMD) expansion.

By decoupling the application from sharding directives, the API enables running
the same application on a single device, multiple devices, or even multiple 
clients, while preserving its global semantics.
"""

"""
## Setup
"""

import keras
from keras import distribution

"""
## DeviceMesh and TensorLayout

The DeviceMesh class in Keras distribution API represents a cluster of 
computational devices configured for distributed computation. It aligns with 
similar concepts in [jax.sharding.Mesh]
(https://jax.readthedocs.io/en/latest/jax.sharding.html#jax.sharding.Mesh) and 
[tf.dtensor.Mesh]
(https://www.tensorflow.org/api_docs/python/tf/experimental/dtensor/Mesh), 
where it's used to map the physical devices to a logical mesh structure.

The `TensorLayout` class then specifies how tensors are distributed across the
`DeviceMesh`, detailing the sharding of tensors along specified axes that 
correspond to the axes names in the `DeviceMesh`.

You can found more detailed concepts in [Tensorflow DTensor guide]
(https://www.tensorflow.org/guide/dtensor_overview#dtensors_model_of_distributed_tensors)
"""

from keras.distribution import DeviceMesh, TensorLayout, list_devices

# Retrieve the local available gpu devices.
devices = list_devices(device_type='gpu')   # Assume it has 8 local GPUs.

# Define a 2x4 device mesh with data and model parallel axes
mesh = DeviceMesh(shape=(2, 4), axis_names=['data', 'model'], devices=devices)

# A 2D layout, which describes how a tensor is distributed across the
# mesh. The layout can be visualized as a 2D grid with 'model' as rows and 
# 'data' as columns, and it is a [4, 2] grid when it mapped to the physcial
# devices on the mesh.
layout_2d = TensorLayout(axes=('model', 'data'), device_mesh=mesh)

# A 4D layout which could be used for data parallel of a image input.
replicated_layout_4d = TensorLayout(axes=('data', None, None, None), 
                                    device_mesh=mesh)

"""
Distribution

The Distribution class in Keras serves as a foundational abstract class designed
for developing custom distribution strategies. It encapsulates the core logic 
needed to distribute a model's variables, input data, and intermediate 
computations across a device mesh. As an end user, you won't have to interact
directly with this class, but its subclasses like `DataParallel` or 
`ModelParallel`.
"""

"""
DataParallel

The `DataParallel` class in the Keras distribution API is designed for the 
data parallelism strategy in distributed training, where the model weights are 
replicated across all devices in the `DeviceMesh`, and each device processes a
portion of the input data.

Here is a sample usage of this class.
"""

from keras.distribution import DataParallel
from keras import layers
from keras import models

# Create with list of devices, as a shortcut, the devices can be skipped, 
# and Keras will detect all local available devices.
# E.g. data_parallel = DataParallel()
data_parallel = DataParallel(devices=list_devices())

# Or you can choose to create with a 1D `DeviceMesh`.
mesh_1d = DeviceMesh(shape=(8,), axis_names=['data'], devices=list_devices())
data_parallel = DataParallel(device_mesh=mesh_1d)

# Note that all the model weights created under the scope are replicated to
# all the devices of the `DeviceMesh`. This include all the weights like RNG
# state, optimizer states, metrics, etc. The dataset feed into `model.fit` or
# `model.evaluate` will be splitted evenly on the batch dimention, and send to
# all the devices. You don't have to do any manual aggregration of losses, 
# since all the computation happens in a global context.
# 
# The `scope` can also be replaced by `keras.distribution.set_distribution()`, 
#  which sets the global distribution.
with data_parallel.scope():
    inputs = layers.Input(shape=[28, 28, 1])
    y = layers.Flatten()(inputs)
    y = layers.Dense(units=200, use_bias=False, activation="relu")(y)
    y = layers.Dropout(0.4)(y)
    y = layers.Dense(units=10, activation="softmax")(y)
    model = models.Model(inputs=inputs, outputs=y)

inputs = np.random.normal(size=(128, 28, 28, 1))
labels = np.random.normal(size=(128, 10))
dataset = tf.data.Dataset.from_tensor_slices((inputs, labels)).batch(16)

with data_parallel.scope():
    model.compile(loss="mse")
    model.fit(dataset, epochs=3)
    model.evaluate(dataset)

"""
ModelParallel and LayoutMap

ModelParallel will be mostly useful when model weights are too large to fit
into a single accelerator. This setting allows you to spit you model weights or
activation tensors across all the devices on the DeviceMesh, and enable the 
horizontal scaling for the large models.

Unlike the `DataParallel` model that all weights are fully replicated, 
the weights layout under `ModelParallel` usually need some customization for 
best performances. We introduce `LayoutMap` to let you specify the 
`TensorLayout` for any weights and intermediate tensors from global perspective.
"""

from keras.distribution import ModelParallel, LayoutMap

