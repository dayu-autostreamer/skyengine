'''
@Project ：SkyEngine 
@File    ：hf_downloader.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/26 14:09
'''
"""
@Project ：cyber_range_platform_v100
@File    ：hf_downloader.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/7/31 15:08
"""

import os
from transformers import AutoModel, AutoTokenizer, AutoConfig
from datasets import (
    load_dataset,
    get_dataset_config_names,
    get_dataset_split_names,
)
from huggingface_hub import snapshot_download


def download_model(model_id: str, save_path: str):
    os.makedirs(save_path, exist_ok=True)
    print(f"[INFO] 开始下载模型: {model_id}")

    AutoConfig.from_pretrained(model_id, cache_dir=save_path)
    AutoTokenizer.from_pretrained(model_id, cache_dir=save_path)
    AutoModel.from_pretrained(model_id, cache_dir=save_path)

    print(f"[SUCCESS] 模型 {model_id} 已保存至: {save_path}")


def download_raw_model(model_id: str, save_path: str):
    print(f"[INFO] 开始下载模型: {model_id}")
    model_dir = snapshot_download(model_id, cache_dir=save_path)
    print(f"[SUCCESS] 模型已保存至: {model_dir}")
    return model_dir


def download_dataset(dataset_id: str, save_path: str):
    os.makedirs(save_path, exist_ok=True)
    print(f"[INFO] 开始下载数据集: {dataset_id}")
    configs = get_dataset_config_names(dataset_id)
    print("可用配置:", configs)

    for config in configs:
        try:
            split_names = get_dataset_split_names(dataset_id, config)
        except Exception:
            split_names = ["train"]

        for split in split_names:
            print(f"[INFO] 下载: config={config}, split={split}")
            try:
                kwargs = {"path": dataset_id, "split": split, "cache_dir": save_path}
                if config:
                    kwargs["name"] = config
                dataset = load_dataset(**kwargs)
                print(f"[SUCCESS] config={config}, split={split}, 样本数={len(dataset)}")
            except Exception as e:
                print(f"[ERROR] config={config}, split={split} 失败: {e}")

    print(f"[SUCCESS] 数据集 {dataset_id} 已缓存至: {save_path}")


def download_raw_dataset_files(dataset_id: str, save_path: str):
    print(f"[INFO] 直接下载原始数据集文件（不验证）: {dataset_id}")
    snapshot_download(
        repo_id=dataset_id,
        repo_type="dataset",
        local_dir=save_path,
        local_dir_use_symlinks=False,
    )
    print(f"[SUCCESS] 完整复制数据集到: {save_path}")


# ================================================================
# 🔥 新增统一入口：通过 Python dict 进行下载
# ================================================================
def download(params: dict):
    """
    params = {
        "local_file_path": "D:/data_model_path",
        "type": "model",  # 或 "dataset"
        "id": "Qwen/Qwen1.5-1.8B"
    }
    """
    required_keys = ["local_file_path", "type", "id"]
    for k in required_keys:
        if k not in params:
            raise ValueError(f"缺少必要参数: {k}")

    save_path = params["local_file_path"]
    os.makedirs(save_path, exist_ok=True)

    d_type = params["type"]
    d_id = params["id"]

    if d_type == "model":
        return download_raw_model(d_id, save_path)

    elif d_type == "dataset":
        dataset_path = os.path.join(save_path, d_id.replace("/", "_"))
        return download_raw_dataset_files(d_id, dataset_path)

    else:
        raise ValueError(f"type 必须是 model 或 dataset，而不是: {d_type}")


# 用例：
if __name__ == "__main__":
    # 示例调用
    download({
        "local_file_path": "D:/Project/finalPro/SkyEngine/dataset",
        "type": "dataset",
        "id": "mideavalwisard/Starjob"
    })
