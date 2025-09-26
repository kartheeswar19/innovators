import os
import json
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam

# =========================
# Paths (updated for your structure)
# =========================
train_dir = 'data/train'        # Using test folder as training data
val_dir = 'data/validation'    # Using validation folder

# =========================
# Image Generators
# =========================
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode='nearest'
)

val_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    color_mode='rgb',
    shuffle=True
)

val_generator = val_datagen.flow_from_directory(
    val_dir,
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    color_mode='rgb',
    shuffle=False
)

# Save class names mapping
class_names = list(train_generator.class_indices.keys())
class_mapping = {i: name for i, name in enumerate(class_names)}

# Save class mapping to JSON file
with open('class_mapping.json', 'w') as f:
    json.dump(class_mapping, f, indent=2)

print(f"Found {train_generator.num_classes} classes:")
for i, name in class_mapping.items():
    print(f"  {i}: {name}")

# =========================
# Model: EfficientNetB0
# =========================
base_model = EfficientNetB0(
    include_top=False,
    weights=None,  # Start without pretrained weights to avoid shape mismatch
    input_shape=(224, 224, 3)
)

# Add custom classification layers
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(512, activation='relu')(x)
predictions = Dense(train_generator.num_classes, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

# Compile model
model.compile(optimizer=Adam(learning_rate=1e-3),
              loss='categorical_crossentropy',
              metrics=['accuracy'])

print("Model summary:")
print(f"Input shape: {model.input_shape}")
print(f"Output shape: {model.output_shape}")
print(f"Total parameters: {model.count_params():,}")

# =========================
# Train the model
# =========================
epochs = 10

print("\nStarting training...")
history = model.fit(
    train_generator,
    validation_data=val_generator,
    epochs=epochs,
    verbose=1
)

# =========================
# Save the model
# =========================
model.save('final_crop_disease_model.keras')
print("Model training complete and saved as final_crop_disease_model.keras")

# Print training summary
print(f"\nTraining Summary:")
print(f"Final training accuracy: {history.history['accuracy'][-1]:.4f}")
print(f"Final validation accuracy: {history.history['val_accuracy'][-1]:.4f}")
