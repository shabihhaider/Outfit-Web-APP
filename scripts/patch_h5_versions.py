import h5py
import json
import os

def fix_h5(path):
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        return
        
    try:
        with h5py.File(path, 'r+') as f:
            if 'model_config' in f.attrs:
                config = f.attrs['model_config']
                if isinstance(config, bytes):
                    config_str = config.decode('utf-8')
                else:
                    config_str = config
                    
                if '"batch_shape":' in config_str:
                    config_str = config_str.replace('"batch_shape":', '"batch_input_shape":')
                    f.attrs['model_config'] = config_str.encode('utf-8')
                    print(f"✅ Successfully patched Keras 3 -> Keras 2 deserialization syntax in {os.path.basename(path)}")
                else:
                    print(f"⚡ {os.path.basename(path)} already compatible or structurally different.")
            else:
                print(f"No model_config found in {os.path.basename(path)}")
    except Exception as e:
        print(f"❌ Error fixing {os.path.basename(path)}: {e}")

print("--- Executing Kaggle H5 Binary Deserialization Patch ---")
fix_h5(r"e:\Final\models\model1_efficientnet_best.h5")
fix_h5(r"e:\Final\models\model1_embedding_extractor.h5")
print("--------------------------------------------------------")
