# COLMAP 视频抽帧工具

用于从视频中稳定抽取高质量帧，适配 COLMAP Sequential SfM。流程包含高频采样、模糊过滤、视差筛选（可选 SSIM 去冗余）。

## 环境配置

- Python 3.14+（见 [.python-version](.python-version)）
- 依赖管理：UV

安装依赖（UV）：
- `uv sync`

## 使用说明

入口： [main.py](main.py)

参数：
- `--video`：输入视频路径（必填）
- `--config`：配置文件路径（默认 config.yaml）
- `--output`：输出目录（覆盖配置中的 output_dir）
- `--log-level`：日志级别（DEBUG/INFO/WARNING/ERROR）

示例（仅说明）：
- 运行入口脚本并传入 `--video` 与可选配置/输出参数

## 配置说明

默认配置在 [config.yaml](./config/video_sampler.yaml)：

- sampling.initial_fps：初始采样帧率
- sampling.blur_threshold：模糊阈值（Laplacian 方差）
- sampling.parallax_threshold_px：视差阈值（像素）
- features.type：ORB 或 SIFT
- features.max_features：最大特征数
- features.min_matches：最小匹配数

详细算法与设计见 [docs/开发文档.md](docs/开发文档.md)
