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
- `--config`：配置文件路径（默认 config/video_sampler.yaml）
- `--output`：输出目录（覆盖配置中的 output_dir）
- `--start-time`：抽帧起始时间（秒，可选）
- `--end-time`：抽帧结束时间（秒，可选）
- `--log-level`：日志级别（DEBUG/INFO/WARNING/ERROR）

示例：
```bash
# 基本用法
uv run python main.py --video videos/dji.mp4

# 带 SRT 文件（自动检测同名 .SRT 文件）
uv run python main.py --video videos/DJI_20260104163018_0024_D.mp4

# 抽取部分视频片段
uv run python main.py --video videos/dji.mp4 --start-time 10 --end-time 60
```

## 功能特性

### 核心抽帧流程
- **高频采样**: 按配置的 FPS 进行初始采样
- **关键帧抽取（可选）**: 支持仅提取视频关键帧（I 帧 / Intra-coded）
- **模糊过滤**: 基于 Laplacian 方差检测并去除运动模糊帧
- **视差筛选**: 使用 ORB/SIFT 特征匹配，确保足够的视差和重叠
- **SSIM 去冗余**: 可选的结构相似性检测，去除近似重复帧

### GPS 元数据支持 🆕
- **自动 SRT 检测**: 检测视频同目录下的同名 SRT 文件
- **GPS 信息解析**: 提取经纬度、相对高度、绝对高度
- **EXIF 嵌入**: 将 GPS 数据写入输出图像的 EXIF（JPEG 格式）
- **COLMAP 兼容**: 生成的图像可直接用于 COLMAP GPS 辅助重建

详细说明见 [SRT 集成说明](docs/SRT集成说明.md)

## 配置说明

默认配置在 [config.yaml](./config/video_sampler.yaml)：

**采样参数**：
- sampling.initial_fps：初始采样帧率
- sampling.blur_threshold：模糊阈值（Laplacian 方差）
- sampling.parallax_threshold_px：视差阈值（像素）
- sampling.only_keyframes：是否仅提取关键帧（I 帧，默认 false）
- sampling.start_time：抽帧起始时间（秒，默认全视频）
- sampling.end_time：抽帧结束时间（秒，默认全视频）

**特征参数**：
- features.type：ORB 或 SIFT
- features.max_features：最大特征数
- features.min_matches：最小匹配数

**质量参数**：
- quality.use_ssim：是否启用SSIM去冗余
- quality.ssim_max：SSIM相似度阈值
- quality.jpeg_quality：JPEG质量（0-100，默认100最高质量）

详细算法与设计见 [docs/开发文档.md](docs/开发文档.md)

版本更新记录见 [docs/CHANGELOG.md](docs/CHANGELOG.md)

## 输出格式

- **有 SRT 元数据**: 输出 JPEG 格式（包含 GPS EXIF，质量100）
- **无 SRT 元数据**: 输出 PNG 格式（保持原逻辑）

输出文件命名: `000000.jpg`, `000001.jpg`, ... (6位补零)

## 开发进度

**🆕 新功能**:
- 支持 DJI SRT 文件自动解析，将 GPS 和高度信息嵌入图像 EXIF，用于 COLMAP 稀疏重建。详见 [SRT 集成说明](docs/SRT集成说明.md)。
- 支持可选“仅提取关键帧（I 帧 / Intra-coded）”。
