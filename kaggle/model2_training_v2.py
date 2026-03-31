"""
PHASE 3: Model 2 MLP Training — v2 (Pairwise Compatibility)
=============================================================
Trains a binary classifier on pairwise compatibility vectors produced
by model2_data_prep_v3.py.

Input:  2570-dim vector [emb_a(1280) + emb_b(1280) + cat_a(5) + cat_b(5)]
Output: compatibility score 0.0 to 1.0

Kaggle Setup:
  1. Run model2_data_prep_v3.py FIRST (produces .npz files in /kaggle/working/)
  2. Paste this script into the NEXT cell and run
  3. Downloads: model2_compatibility_scorer.h5, model2_results.json
"""

import os
import json
import time
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, Callback
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for Kaggle
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SCRIPT_START = time.time()
TOTAL_STEPS = 9

def phase(num, desc):
    elapsed = time.time() - SCRIPT_START
    pct = int(num / TOTAL_STEPS * 100)
    print(f"\n{'='*60}")
    print(f"  STEP {num}/{TOTAL_STEPS} — {desc}  [{pct}% overall | {elapsed:.0f}s elapsed]")
    print(f"{'='*60}")

# ─── CUSTOM EPOCH PROGRESS CALLBACK ─────────────────────────────
class TrainingProgress(Callback):
    """Shows overall training progress with key metrics per epoch."""
    def __init__(self, total_epochs):
        self.total_epochs = total_epochs
        self.best_val_auc = 0
        self.train_start = None

    def on_train_begin(self, logs=None):
        self.train_start = time.time()
        print(f"\n  {'Epoch':>5}  {'Loss':>8}  {'Acc':>7}  {'AUC':>7}  {'V_Loss':>8}  {'V_Acc':>7}  {'V_AUC':>7}  {'Progress'}")
        print(f"  {'─'*5}  {'─'*8}  {'─'*7}  {'─'*7}  {'─'*8}  {'─'*7}  {'─'*7}  {'─'*20}")

    def on_epoch_end(self, epoch, logs=None):
        e = epoch + 1
        pct = int(e / self.total_epochs * 100)
        filled = int(15 * e / self.total_epochs)
        bar = "█" * filled + "░" * (15 - filled)

        val_auc = logs.get('val_auc_roc', 0)
        if val_auc > self.best_val_auc:
            self.best_val_auc = val_auc
            marker = " ★ best"
        else:
            marker = ""

        elapsed = time.time() - self.train_start
        eta = elapsed / e * (self.total_epochs - e) if e < self.total_epochs else 0

        print(f"  {e:>5}  {logs.get('loss',0):>8.4f}  {logs.get('accuracy',0):>6.1%}  {logs.get('auc_roc',0):>6.4f}"
              f"  {logs.get('val_loss',0):>8.4f}  {logs.get('val_accuracy',0):>6.1%}  {val_auc:>6.4f}"
              f"  |{bar}| {pct:3d}% ETA {eta:.0f}s{marker}")

    def on_train_end(self, logs=None):
        elapsed = time.time() - self.train_start
        print(f"\n  Training finished in {elapsed/60:.1f} minutes")
        print(f"  Best val AUC-ROC: {self.best_val_auc:.4f}")


print("=" * 60)
print("  PHASE 3: MODEL 2 MLP TRAINING (v2 — Pairwise)")
print("=" * 60)

# ─── STEP 1/9: LOAD DATA ────────────────────────────────────────
phase(1, "LOAD DATA")

train = np.load("/kaggle/working/model2_train.npz")
val = np.load("/kaggle/working/model2_val.npz")
test = np.load("/kaggle/working/model2_test.npz")

X_train, y_train = train['X'], train['y']
X_val, y_val = val['X'], val['y']
X_test, y_test = test['X'], test['y']

print(f"  Train: {X_train.shape} — pos: {int(y_train.sum()):,} neg: {int(len(y_train) - y_train.sum()):,}")
print(f"  Val:   {X_val.shape}  — pos: {int(y_val.sum()):,} neg: {int(len(y_val) - y_val.sum()):,}")
print(f"  Test:  {X_test.shape} — pos: {int(y_test.sum()):,} neg: {int(len(y_test) - y_test.sum()):,}")

INPUT_DIM = X_train.shape[1]
print(f"  Input dimension: {INPUT_DIM}")

meta_path = "/kaggle/working/model2_metadata.json"
if os.path.exists(meta_path):
    with open(meta_path) as f:
        metadata = json.load(f)
    print(f"  Architecture: {metadata['architecture']}")
    print(f"  Vector layout: {metadata['vector_layout']}")
print("  [OK] Data loaded")

# ─── STEP 2/9: BUILD MODEL ──────────────────────────────────────
phase(2, "BUILD MODEL")

model = Sequential([
    Input(shape=(INPUT_DIM,)),

    Dense(1024, activation='relu'),
    BatchNormalization(),
    Dropout(0.4),

    Dense(512, activation='relu'),
    BatchNormalization(),
    Dropout(0.3),

    Dense(256, activation='relu'),
    BatchNormalization(),
    Dropout(0.2),

    Dense(128, activation='relu'),
    Dropout(0.1),

    Dense(1, activation='sigmoid')
])

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss='binary_crossentropy',
    metrics=[
        'accuracy',
        tf.keras.metrics.AUC(name='auc_roc', curve='ROC'),
        tf.keras.metrics.Precision(name='precision'),
        tf.keras.metrics.Recall(name='recall'),
    ]
)

model.summary()
print(f"\n  Total parameters: {model.count_params():,}")
print("  [OK] Model built")

# ─── STEP 3/9: CONFIGURE TRAINING ───────────────────────────────
phase(3, "CONFIGURE TRAINING")

MAX_EPOCHS = 50
BATCH_SIZE = 256
steps_per_epoch = len(X_train) // BATCH_SIZE
est_time_per_epoch = steps_per_epoch * 0.15  # rough estimate

print(f"  Max epochs: {MAX_EPOCHS}")
print(f"  Batch size: {BATCH_SIZE}")
print(f"  Steps/epoch: {steps_per_epoch}")
print(f"  Early stopping patience: 8 epochs (on val_auc_roc)")
print(f"  LR reduction patience: 3 epochs")
print(f"  Estimated time/epoch: ~{est_time_per_epoch:.0f}s")
print(f"  Estimated total: ~{est_time_per_epoch * 20 / 60:.0f}-{est_time_per_epoch * MAX_EPOCHS / 60:.0f} min (with early stopping)")

callbacks = [
    EarlyStopping(
        monitor='val_auc_roc',
        patience=8,
        mode='max',
        restore_best_weights=True,
        verbose=0,  # our custom callback handles output
    ),
    ReduceLROnPlateau(
        monitor='val_auc_roc',
        factor=0.5,
        patience=3,
        mode='max',
        min_lr=1e-6,
        verbose=0,
    ),
    ModelCheckpoint(
        '/kaggle/working/model2_best_checkpoint.keras',
        monitor='val_auc_roc',
        mode='max',
        save_best_only=True,
        verbose=0,
    ),
    TrainingProgress(total_epochs=MAX_EPOCHS),
]
print("  [OK] Callbacks configured")

# ─── STEP 4/9: TRAIN ────────────────────────────────────────────
phase(4, "TRAINING (GPU)")

history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=MAX_EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=callbacks,
    verbose=0,  # using custom TrainingProgress callback instead
)

epochs_trained = len(history.history['loss'])
best_epoch = np.argmax(history.history['val_auc_roc']) + 1
best_val_auc = max(history.history['val_auc_roc'])
print(f"  Stopped at epoch {epochs_trained}/{MAX_EPOCHS}")
print(f"  Best epoch: {best_epoch} (val_auc_roc = {best_val_auc:.4f})")
print("  [OK] Training complete")

# ─── STEP 5/9: EVALUATE ON TEST SET ─────────────────────────────
phase(5, "EVALUATE ON TEST SET")

y_pred_proba = model.predict(X_test, verbose=0).flatten()
y_pred_binary = (y_pred_proba >= 0.5).astype(int)

auc_roc = roc_auc_score(y_test, y_pred_proba)
test_loss, test_acc, test_auc, test_prec, test_rec = model.evaluate(X_test, y_test, verbose=0)
f1 = 2 * test_prec * test_rec / (test_prec + test_rec + 1e-8)

print(f"\n  ┌─────────────────────────────────────────┐")
print(f"  │  AUC-ROC:   {auc_roc:.4f}", end="")
if auc_roc >= 0.75:
    print(f"   ✓ TARGET MET          │")
elif auc_roc >= 0.65:
    print(f"   ~ ACCEPTABLE          │")
else:
    print(f"   ✗ BELOW TARGET        │")
print(f"  │  Accuracy:  {test_acc:.4f}                        │")
print(f"  │  Precision: {test_prec:.4f}                        │")
print(f"  │  Recall:    {test_rec:.4f}                        │")
print(f"  │  F1-Score:  {f1:.4f}                        │")
print(f"  └─────────────────────────────────────────┘")

print(f"\n  Classification Report:")
print(classification_report(y_test, y_pred_binary,
                            target_names=['Incompatible', 'Compatible']))

cm = confusion_matrix(y_test, y_pred_binary)
print(f"  Confusion Matrix:")
print(f"    TN={cm[0][0]:,}  FP={cm[0][1]:,}")
print(f"    FN={cm[1][0]:,}  TP={cm[1][1]:,}")
print("  [OK] Evaluation complete")

# ─── STEP 6/9: VISUALIZE ──────────────────────────────────────────
phase(6, "VISUALIZE (Training Curves, ROC, Confusion Matrix)")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Model 2 — Pairwise Compatibility Scorer', fontsize=14, fontweight='bold')

# Plot 1: Loss curves
ax = axes[0, 0]
ax.plot(history.history['loss'], label='Train Loss', linewidth=1.5)
ax.plot(history.history['val_loss'], label='Val Loss', linewidth=1.5)
ax.axvline(x=best_epoch - 1, color='gray', linestyle='--', alpha=0.5, label=f'Best epoch ({best_epoch})')
ax.set_title('Loss')
ax.set_xlabel('Epoch')
ax.set_ylabel('Binary Crossentropy')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 2: Accuracy curves
ax = axes[0, 1]
ax.plot(history.history['accuracy'], label='Train Acc', linewidth=1.5)
ax.plot(history.history['val_accuracy'], label='Val Acc', linewidth=1.5)
ax.axvline(x=best_epoch - 1, color='gray', linestyle='--', alpha=0.5, label=f'Best epoch ({best_epoch})')
ax.set_title('Accuracy')
ax.set_xlabel('Epoch')
ax.set_ylabel('Accuracy')
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 3: AUC-ROC curves
ax = axes[1, 0]
ax.plot(history.history['auc_roc'], label='Train AUC', linewidth=1.5)
ax.plot(history.history['val_auc_roc'], label='Val AUC', linewidth=1.5)
ax.axhline(y=0.75, color='green', linestyle=':', alpha=0.5, label='Target (0.75)')
ax.axvline(x=best_epoch - 1, color='gray', linestyle='--', alpha=0.5, label=f'Best epoch ({best_epoch})')
ax.set_title('AUC-ROC')
ax.set_xlabel('Epoch')
ax.set_ylabel('AUC-ROC')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 4: ROC Curve on test set
from sklearn.metrics import roc_curve
fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
ax = axes[1, 1]
ax.plot(fpr, tpr, linewidth=2, label=f'ROC (AUC = {auc_roc:.4f})')
ax.plot([0, 1], [0, 1], 'k--', alpha=0.4, label='Random (AUC = 0.5)')
ax.fill_between(fpr, tpr, alpha=0.1)
ax.set_title('ROC Curve (Test Set)')
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.legend(loc='lower right')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/kaggle/working/model2_training_curves.png', dpi=150, bbox_inches='tight')
plt.show()
print("  Saved: model2_training_curves.png")

# Confusion matrix heatmap
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
ax.figure.colorbar(im, ax=ax)
ax.set(xticks=[0, 1], yticks=[0, 1],
       xticklabels=['Incompatible', 'Compatible'],
       yticklabels=['Incompatible', 'Compatible'],
       xlabel='Predicted', ylabel='Actual',
       title='Confusion Matrix (Test Set)')

# Annotate cells with counts and percentages
total = cm.sum()
for i in range(2):
    for j in range(2):
        count = cm[i, j]
        pct = count / total * 100
        ax.text(j, i, f'{count:,}\n({pct:.1f}%)',
                ha='center', va='center', fontsize=12,
                color='white' if count > total / 4 else 'black')

plt.tight_layout()
plt.savefig('/kaggle/working/model2_confusion_matrix.png', dpi=150, bbox_inches='tight')
plt.show()
print("  Saved: model2_confusion_matrix.png")

# Precision-Recall curve
from sklearn.metrics import precision_recall_curve, average_precision_score
precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_pred_proba)
avg_prec = average_precision_score(y_test, y_pred_proba)

fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(recall_vals, precision_vals, linewidth=2, label=f'PR (AP = {avg_prec:.4f})')
ax.fill_between(recall_vals, precision_vals, alpha=0.1)
ax.set_title('Precision-Recall Curve (Test Set)')
ax.set_xlabel('Recall')
ax.set_ylabel('Precision')
ax.legend(loc='lower left')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('/kaggle/working/model2_precision_recall.png', dpi=150, bbox_inches='tight')
plt.show()
print("  Saved: model2_precision_recall.png")
print("  [OK] All plots saved")

# ─── STEP 7/9: SAVE EVALUATION REPORT ─────────────────────────────
phase(7, "SAVE EVALUATION REPORT")

report_text = classification_report(y_test, y_pred_binary,
                                    target_names=['Incompatible', 'Compatible'])

eval_report = f"""Model 2 — Pairwise Compatibility Scorer — Evaluation Report
{'='*60}

Architecture: MLP (2570 → 1024 → 512 → 256 → 128 → 1)
Input: [emb_a(1280) + emb_b(1280) + cat_a(5) + cat_b(5)]
Training pairs: {len(y_train):,}
Validation pairs: {len(y_val):,}
Test pairs: {len(y_test):,}

Training Summary
{'-'*40}
  Epochs trained: {epochs_trained}/{MAX_EPOCHS}
  Best epoch: {best_epoch}
  Best val AUC-ROC: {best_val_auc:.4f}

Test Set Metrics
{'-'*40}
  AUC-ROC:        {auc_roc:.4f}  {'✓ TARGET MET' if auc_roc >= 0.75 else '~ ACCEPTABLE' if auc_roc >= 0.65 else '✗ BELOW TARGET'}
  Accuracy:       {test_acc:.4f}
  Precision:      {test_prec:.4f}
  Recall:         {test_rec:.4f}
  F1-Score:       {f1:.4f}
  Avg Precision:  {avg_prec:.4f}

Classification Report
{'-'*40}
{report_text}

Confusion Matrix
{'-'*40}
  TN (correct incompatible): {cm[0][0]:,}
  FP (false compatible):     {cm[0][1]:,}
  FN (false incompatible):   {cm[1][0]:,}
  TP (correct compatible):   {cm[1][1]:,}

  Total test pairs: {cm.sum():,}
  Correct: {cm[0][0] + cm[1][1]:,} ({(cm[0][0] + cm[1][1]) / cm.sum() * 100:.1f}%)

Saved Artifacts
{'-'*40}
  model2_compatibility_scorer.h5      — trained model (H5 format)
  model2_compatibility_scorer.keras   — trained model (Keras format)
  model2_results.json                 — metrics + metadata
  model2_evaluation.txt               — this report
  model2_training_curves.png          — loss/accuracy/AUC plots + ROC curve
  model2_confusion_matrix.png         — confusion matrix heatmap
  model2_precision_recall.png         — precision-recall curve
{'='*60}
"""

with open('/kaggle/working/model2_evaluation.txt', 'w') as f:
    f.write(eval_report)
print(eval_report)
print("  Saved: model2_evaluation.txt")
print("  [OK] Evaluation report saved")

# ─── STEP 8/9: SAVE MODEL ───────────────────────────────────────
phase(8, "SAVE MODEL")

model.save('/kaggle/working/model2_compatibility_scorer.h5')
model.save('/kaggle/working/model2_compatibility_scorer.keras')
print("  Saved: model2_compatibility_scorer.h5")
print("  Saved: model2_compatibility_scorer.keras")

metadata_out = {
    "input_dim": INPUT_DIM,
    "architecture": "pairwise",
    "vector_layout": f"emb_a + emb_b + cat_a_onehot + cat_b_onehot = {INPUT_DIM}-dim",
    "category_order": ["bottom", "dress", "outwear", "shoes", "top"],
    "num_categories": 5,
    "test_auc_roc": float(auc_roc),
    "test_accuracy": float(test_acc),
    "test_precision": float(test_prec),
    "test_recall": float(test_rec),
    "test_f1": float(f1),
    "best_epoch": int(best_epoch),
    "epochs_trained": int(epochs_trained),
    "train_pairs": int(len(y_train)),
    "val_pairs": int(len(y_val)),
    "test_pairs": int(len(y_test)),
    "scoring_note": "At inference, score each item pair in outfit, then average all pair scores",
}
with open("/kaggle/working/model2_results.json", "w") as f:
    json.dump(metadata_out, f, indent=2)
print("  Saved: model2_results.json")
print("  [OK] Model saved")

# ─── STEP 9/9: INFERENCE GUIDE ──────────────────────────────────
phase(9, "INFERENCE GUIDE")

print("""
  How to use at runtime (Phase 4 recommendation engine):

  model2 = load_model('model2_compatibility_scorer.h5')
  embedding_model = load_model('model1_embedding_extractor.h5')

  For an outfit [top, bottom, shoes]:
    emb_top    = embedding_model.predict(top_image)
    emb_bottom = embedding_model.predict(bottom_image)
    emb_shoes  = embedding_model.predict(shoes_image)

    cat_top    = [0, 0, 0, 0, 1]  # 'top' is index 4
    cat_bottom = [1, 0, 0, 0, 0]  # 'bottom' is index 0
    cat_shoes  = [0, 0, 0, 1, 0]  # 'shoes' is index 3

    pair_1 = concat([emb_top, emb_bottom, cat_top, cat_bottom])  -> score
    pair_2 = concat([emb_top, emb_shoes, cat_top, cat_shoes])    -> score
    pair_3 = concat([emb_bottom, emb_shoes, cat_bottom, cat_shoes]) -> score

    compatibility_score = average(pair_1, pair_2, pair_3)
    (This goes into Gate 3 as the 0.50 weight component)
""")

# ─── FINAL SUMMARY ──────────────────────────────────────────────
total_time = time.time() - SCRIPT_START
print("=" * 60)
print("  MODEL 2 TRAINING COMPLETE")
print(f"  Total time: {total_time/60:.1f} minutes")
print(f"  Test AUC-ROC: {auc_roc:.4f}")
print(f"  Best epoch: {best_epoch}/{epochs_trained}")
print(f"")
print(f"  Download from /kaggle/working/:")
print(f"    model2_compatibility_scorer.h5  -> models/")
print(f"    model2_results.json             -> models/")
print(f"    model2_evaluation.txt           -> models/")
print(f"    model2_training_curves.png      -> models/ (for FYP report)")
print(f"    model2_confusion_matrix.png     -> models/ (for FYP report)")
print(f"    model2_precision_recall.png     -> models/ (for FYP report)")
print("=" * 60)
