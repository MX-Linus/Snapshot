"""
Title: Trainer pattern
Author: [nkovela1](https://nkovela1.github.io/)
Date created: 2022/09/19
Last modified: 2022/09/23
Description: Guide on how to share a custom training step across multiple Keras models.
"""
"""
## Introduction

This example shows how to create a custom training step using the Trainer pattern, which can then be shared across multiple Keras models. This pattern overrides the train_step method of the keras.Model class, allowing for the addition of custom loss functions and metrics.

The Trainer pattern can also easily be adapted to more complex models with larger custom training steps, such as this [end-to-end GAN model](https://keras.io/guides/customizing_what_happens_in_fit/#wrapping-up-an-endtoend-gan-example), by putting the custom training step in the Trainer class definition.
"""

"""
## Setup
"""

import tensorflow as tf
from tensorflow import keras

# Load MNIST dataset and normalize
mnist = keras.datasets.mnist
(x_train, y_train),(x_test, y_test) = mnist.load_data()
x_train, x_test = x_train / 255.0, x_test / 255.0


"""
## Sharing custom training step across multiple models

A custom training step can be created by overriding the train_step method of a Model subclass.
""" 
class MyTrainer(keras.Model):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def train_step(self, data):
        x, y = data
        with tf.GradientTape() as tape:
            y_pred = self.model(x, training=True) # Forward pass
            # Compute loss value
            loss = self.compiled_loss(y, y_pred, regularization_losses=self.losses)

        # Compute gradients
        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)

        # Update weights
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))

        # Update metrics configured in `compile()`
        self.compiled_metrics.update_state(y, y_pred)

        # Return a dict mapping metric names to current value.
        return {m.name: m.result() for m in self.metrics}
    
    def call(self, x):
	# Equivalent to `call()` of the wrapped keras.Model
	x = self.model(x)
	return x

"""
## Define multiple models to share the custom training step

Let's define two different models that can share our Trainer class and its custom train_step
"""

# A model defined using Sequential API
MyModel = keras.models.Sequential([
    keras.layers.Flatten(input_shape=(28,28)),
    keras.layers.Dense(256, activation='relu'),
    keras.layers.Dropout(0.2),
    keras.layers.Dense(10, activation='softmax')
])

# A model defined using Functional API
func_input = keras.Input(shape=(28,28,1))
x = keras.layers.Flatten(input_shape=(28,28))(func_input)
x = keras.layers.Dense(512, activation='relu')(x)
x = keras.layers.Dropout(0.4)(x)
func_output = keras.layers.Dense(10, activation='softmax')(x)

YourModel = keras.Model(func_input, func_output)

"""
## Create Trainer class objects from the models
"""
trainer_1 = MyTrainer(MyModel)
trainer_2 = MyTrainer(YourModel)

"""
## Compile and fit the models to the MNIST dataset
"""
trainer_1.compile(keras.optimizers.SGD(), loss='sparse_categorical_crossentropy', metrics=['accuracy'])
trainer_1.fit(x_train, y_train, epochs=5, batch_size=64, validation_data=(x_test, y_test))

trainer_2.compile(keras.optimizers.Adam(), loss='sparse_categorical_crossentropy', metrics=['accuracy'])
trainer_2.fit(x_train, y_train, epochs=5, batch_size=64, validation_data=(x_test, y_test))


