"""
PHASE 3: Model 2 MLP Training — Fixed Version
===============================================
Trains the compatibility scorer on the 5123-dim vectors produced by
the data prep script.

Input: [top_1280 + bottom_1280 + outwear_1280 + shoes_1280 + occasion_3]
Output: compatibility score (0.0 to 1.0)
Target: AUC-ROC > 0.75

Run this in the SAME Kaggle notebook, in a new cell AFTER data prep completes.
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from tensorflow.keras import regularizers
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, roc_auc_score

print("=" * 60)
print("  PHASE 3: MODEL 2 MLP TRAINING")
print("=" * 60)

# ─── 1. LOAD DATA ───────────────────────────────────────────────
def load_npz(path):
    data = np.load(path)
    return data['X'], data['y']

X_train, y_train = load_npz("/kaggle/working/model2_train.npz")
X_val, y_val     = load_npz("/kaggle/working/model2_val.npz")
X_test, y_test   = load_npz("/kaggle/working/model2_test.npz")

print(f"Train: X={X_train.shape}, y={y_train.shape}")
print(f"Val:   X={X_val.shape}, y={y_val.shape}")
print(f"Test:  X={X_test.shape}, y={y_test.shape}")

INPUT_DIM = X_train.shape[1]
print(f"\nInput dimension: {INPUT_DIM}")

# ─── 2. CLASS WEIGHTS ───────────────────────────────────────────
class_weights_array = compute_class_weight(
    class_weight='balanced',
    classes=np.unique(y_train),
    y=y_train
)
class_weights = {0: class_weights_array[0], 1: class_weights_array[1]}
print(f"\nClass weights:")
print(f"  Incompatible (0): {class_weights[0]:.3f}")
print(f"  Compatible (1):   {class_weights[1]:.3f}")

# ─── 3. MLP ARCHITECTURE ────────────────────────────────────────
print(f"\nBuilding MLP for {INPUT_DIM}-dim input...")
model = Sequential([
    tf.keras.Input(shape=(INPUT_DIM,)),

    Dense(512, activation='relu', kernel_regularizer=regularizers.l2(1e-4)),
    BatchNormalization(),
    Dropout(0.4),

    Dense(256, activation='relu', kernel_regularizer=regularizers.l2(1e-4)),
    BatchNormalization(),
    Dropout(0.3),

    Dense(64, activation='relu'),
    Dropout(0.2),

    Dense(1, activation='sigmoid', name='compatibility_score')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss='binary_crossentropy',
    metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
)

model.summary()

# ─── 4. TRAINING ────────────────────────────────────────────────
callbacks = [
    ModelCheckpoint(
        '/kaggle/working/model2_compatibility_engine.h5',
        monitor='val_auc',
        save_best_only=True,
        mode='max',
        verbose=1
    ),
    EarlyStopping(
        monitor='val_auc',
        patience=8,
        restore_best_weights=True,
        mode='max',
        verbose=1
    ),
    ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.3,
        patience=3,
        min_lr=1e-6,
        verbose=1
    )
]

print("\n" + "=" * 60)
print("  TRAINING START")
print("=" * 60)

history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=40,
    batch_size=128,
    class_weight=class_weights,
    callbacks=callbacks
)

# ─── 5. EVALUATION ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("  EVALUATION ON TEST SET")
print("=" * 60)

model.load_weights('/kaggle/working/model2_compatibility_engine.h5')

test_loss, test_acc, test_auc = model.evaluate(X_test, y_test, verbose=0)
print(f"\nTest AUC-ROC:  {test_auc:.4f}")
print(f"Test Accuracy: {test_acc:.4f}")

if test_auc >= 0.75:
    print("PASSED: AUC-ROC target (>= 0.75)")
else:
    print(f"BELOW TARGET: AUC-ROC is {test_auc:.4f}, target is 0.75")

y_pred_probs = model.predict(X_test, verbose=0).flatten()
y_pred_classes = (y_pred_probs > 0.5).astype(int)

report = classification_report(
    y_test, y_pred_classes,
    target_names=["Incompatible (0)", "Compatible (1)"]
)
print(f"\n{report}")

# Verify with sklearn's AUC-ROC (independent check)
sklearn_auc = roc_auc_score(y_test, y_pred_probs)
print(f"sklearn AUC-ROC (verification): {sklearn_auc:.4f}")

# Save evaluation report
with open('/kaggle/working/model2_evaluation_report.txt', 'w') as f:
    f.write("Model 2 — MLP Compatibility Scorer\n")
    f.write("=" * 50 + "\n")
    f.write(f"Input dimension: {INPUT_DIM}\n")
    f.write(f"Vector layout: top + bottom + outwear + shoes + occasion\n")
    f.write(f"Test AUC-ROC:  {test_auc:.4f}\n")
    f.write(f"Test Accuracy: {test_acc:.4f}\n")
    f.write(f"sklearn AUC:   {sklearn_auc:.4f}\n")
    f.write("=" * 50 + "\n")
    f.write(report)

print("\n" + "=" * 60)
print("  TRAINING COMPLETE")
print("=" * 60)
print("\nDownload these files from /kaggle/working/:")
print("  1. model2_compatibility_engine.h5  -> models/")
print("  2. model2_evaluation_report.txt    -> Resources/model 2/")
print("=" * 60)
