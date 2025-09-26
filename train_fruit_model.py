import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import ResNet50V2
from tensorflow.keras.optimizers import Adam

# Configuration
DATA_PATH = 'data/fruit_diseases'     # root folder containing subfolders per fruit class
MODEL_SAVE_PATH = 'models/fruit_model.keras'
CLASSES_SAVE_PATH = 'mappings/fruit_classes.json'
IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 30
LR = 1e-4
VAL_SPLIT = 0.2

# Ensure output dirs exist
os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(CLASSES_SAVE_PATH), exist_ok=True)

# Data generators
datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=30,
    width_shift_range=0.2,
    height_shift_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    validation_split=VAL_SPLIT
)

train_gen = datagen.flow_from_directory(
    DATA_PATH, target_size=IMG_SIZE, batch_size=BATCH_SIZE,
    class_mode='categorical', subset='training', shuffle=True
)
val_gen = datagen.flow_from_directory(
    DATA_PATH, target_size=IMG_SIZE, batch_size=BATCH_SIZE,
    class_mode='categorical', subset='validation', shuffle=False
)

# Save class mapping
with open(CLASSES_SAVE_PATH, 'w') as f:
    json.dump({v: k for k, v in train_gen.class_indices.items()}, f, indent=2)
print(f"Classes saved to {CLASSES_SAVE_PATH}")

# Build model
base = ResNet50V2(weights='imagenet', include_top=False, input_shape=(*IMG_SIZE,3))
base.trainable = False

model = models.Sequential([
    base,
    layers.GlobalAveragePooling2D(),
    layers.Dropout(0.5),
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(train_gen.num_classes, activation='softmax')
])

model.compile(optimizer=Adam(LR), loss='categorical_crossentropy', metrics=['accuracy'])
model.summary()

# Train
callbacks = [
    tf.keras.callbacks.EarlyStopping(monitor='val_accuracy', patience=5, restore_best_weights=True),
    tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3)
]
history = model.fit(train_gen, epochs=EPOCHS, validation_data=val_gen, callbacks=callbacks)

# Fine-tune
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False

model.compile(optimizer=Adam(LR/10), loss='categorical_crossentropy', metrics=['accuracy'])
model.fit(train_gen, epochs=EPOCHS, validation_data=val_gen, callbacks=callbacks, initial_epoch=len(history.history['loss']))

# Save final model
model.save(MODEL_SAVE_PATH)
print(f"Fruit model saved to {MODEL_SAVE_PATH}")
