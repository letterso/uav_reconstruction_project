# SRT 元数据集成功能说明

## 概述

该项目现已支持从 DJI 无人机视频的 SRT 字幕文件中提取 GPS 和高度信息，并将其嵌入到抽帧后的图像 EXIF 中，用于 COLMAP 稀疏重建。

## 功能特性

### 1. 自动 SRT 检测
- 在视频抽帧时，自动检测视频同级目录下是否存在同名 SRT 文件
- 支持 `.SRT` 和 `.srt` 扩展名
- 如果没有 SRT 文件，保持原有处理流程不变

### 2. SRT 元数据解析
新模块 `video_sampler/srt_parser.py` 实现了完整的 DJI SRT 解析功能：

- **解析内容**：
  - GPS 坐标（经度、纬度）
  - 相对高度（rel_alt）
  - 绝对高度（abs_alt）
  - 帧编号和时间戳
  - 相机设置（ISO、快门速度等，可选）

- **核心类**：
  - `SRTFrameMetadata`: 单帧元数据数据类
  - `SRTParser`: SRT 文件解析器
  - `find_srt_file()`: 自动查找 SRT 文件

### 3. EXIF 元数据写入
新模块 `video_sampler/exif_writer.py` 负责将 GPS 信息写入图像：

- **EXIF 字段**：
  - `GPSLatitude` / `GPSLatitudeRef`: 纬度（度/分/秒格式）
  - `GPSLongitude` / `GPSLongitudeRef`: 经度（度/分/秒格式）
  - `GPSAltitude` / `GPSAltitudeRef`: 高度（米）
  - `ISOSpeedRatings`: ISO 值（可选）

- **文件格式与质量**：
  - 有 GPS 元数据时：输出 JPEG 格式（EXIF 支持）
  - 无 GPS 元数据时：输出 PNG 格式（保持原逻辑）
  - **JPEG 质量**：默认 100（最高质量，可配置）
  - **优化参数**：
    - Huffman 优化：启用
    - 渐进式编码：禁用（保证质量）
    - Luma/Chroma 质量：与主质量参数一致

### 4. 主流程集成
`video_sampler/extract_frames.py` 已更新以支持：

- 在采样开始时检测并加载 SRT 文件
- 对每个保留的帧，根据时间戳查找对应的 GPS 元数据
- 自动选择输出格式（JPEG 或 PNG）
- 日志中显示是否包含 GPS 信息

## 使用方法

### 基本用法

```bash
# 准备视频文件和对应的 SRT 文件
videos/
  ├── DJI_20260104163018_0024_D.mp4
  └── DJI_20260104163018_0024_D.SRT  # 同名 SRT 文件

# 运行抽帧（会自动检测并使用 SRT）
uv run python main.py --video videos/DJI_20260104163018_0024_D.mp4
```

### 输出示例

**有 SRT 文件时**：
```
[INFO] Found SRT file: videos/DJI_20260104163018_0024_D.SRT
[INFO] Parsed 5794 frame metadata entries from SRT
[INFO] SRT metadata will be embedded in output images
[INFO] Keep frame 0 at 0.000s -> images/000000.jpg (with GPS)
[INFO] Keep frame 32 at 1.200s -> images/000001.jpg (with GPS)
```

**无 SRT 文件时**：
```
[INFO] No SRT file found, proceeding without GPS metadata
[INFO] Keep frame 0 at 0.000s -> images/000000.png
[INFO] Keep frame 32 at 1.200s -> images/000001.png
```

### 验证 EXIF 信息

使用 Python 读取 EXIF：

```python
import piexif
from pathlib import Path

# 读取图像 EXIF
exif_dict = piexif.load("images/000000.jpg")

# 提取 GPS 信息
gps = exif_dict["GPS"]
latitude = gps[piexif.GPSIFD.GPSLatitude]
longitude = gps[piexif.GPSIFD.GPSLongitude]
altitude = gps[piexif.GPSIFD.GPSAltitude]

print(f"GPS: {latitude}, {longitude}, Altitude: {altitude}m")
```

使用 exiftool 命令行工具：

```bash
exiftool images/000000.jpg | grep GPS
# 输出:
# GPS Latitude                    : 23 deg 11' 1.67"
# GPS Longitude                   : 113 deg 25' 7.35"
# GPS Altitude                    : 14.6 m
```

## COLMAP 集成

COLMAP 可以使用图像 EXIF 中的 GPS 信息进行初始化和优化：

```bash
# COLMAP 自动检测 GPS EXIF
colmap feature_extractor \
  --image_path images \
  --database_path database.db

colmap exhaustive_matcher \
  --database_path database.db

colmap mapper \
  --database_path database.db \
  --image_path images \
  --output_path sparse
```

COLMAP 将自动使用 GPS 数据作为初始估计，提高重建成功率和精度。

## 配置参数

所有参数在 `config/video_sampler.yaml` 中配置：

```yaml
sampling:
  initial_fps: 5
  blur_threshold: 150
  parallax_threshold_px: 100
  # ... 其他参数

quality:
  use_ssim: true
  ssim_max: 0.98
  jpeg_quality: 100  # JPEG质量 (0-100)，100=最高质量
```

**JPEG 质量说明**：
- **100**（默认）: 最高质量，适合3D重建，文件较大
- **95-98**: 极高质量，文件大小减少20-30%，视觉无损
- **85-90**: 高质量，文件大小减少50%，轻微质量损失
- 建议保持 100 以确保COLMAP重建精度

### GPS 坐标格式转换

SRT 中的 GPS 坐标是十进制格式（如 `23.183797`），需要转换为 EXIF 的度/分/秒格式：

```python
degrees = int(decimal)
minutes = int((decimal - degrees) * 60)
seconds = ((decimal - degrees) * 60 - minutes) * 60

# EXIF 格式: ((degrees, 1), (minutes, 1), (seconds*10000, 10000))
```

### 时间戳匹配

- SRT 中的时间戳格式: `HH:MM:SS,mmm`
- 视频帧时间戳: 秒数（浮点数）
- 匹配算法: 找到时间戳差值最小的 SRT 帧

### 文件格式选择

- **JPEG**: 支持 EXIF，用于有 GPS 数据的帧
- **PNG**: 不支持 EXIF，用于无 GPS 数据的情况（保持原逻辑）

## 依赖项

新增依赖（已添加到 `pyproject.toml`）：

```toml
piexif>=1.1.3  # EXIF 读写库
```

安装依赖：

```bash
uv sync
```

## 文件结构

```
video_sampler/
  ├── __init__.py
  ├── srt_parser.py        # 新增: SRT 解析器
  ├── exif_writer.py       # 新增: EXIF 写入器
  ├── extract_frames.py    # 修改: 集成 SRT 和 EXIF
  ├── blur_filter.py
  ├── parallax_filter.py
  ├── video_io.py
  └── config.py
```

## 注意事项

1. **SRT 文件必须与视频同名**：如 `video.mp4` 对应 `video.SRT`
2. **JPEG 质量固定为 95%**：平衡文件大小和图像质量
3. **高度使用相对高度**：`rel_alt` 比 `abs_alt` 对无人机航拍更准确
4. **时间戳匹配容差**：自动匹配最接近的 SRT 帧，通常误差小于 1 帧（~16ms）
5. **EXIF 写入失败会降级**：如果 EXIF 写入失败，仍会保存图像（无 GPS）

## 测试

已通过以下测试：

- ✅ SRT 文件解析（5794 帧元数据）
- ✅ GPS 坐标 EXIF 写入和读取
- ✅ 时间戳匹配精度（<20ms）
- ✅ 与原流程的兼容性（无 SRT 时）

## 示例数据

项目包含真实的 DJI 视频和 SRT 文件用于测试：

```
videos/DJI_20260104163018_0024_D.mp4  # DJI 无人机视频
videos/DJI_20260104163018_0024_D.SRT  # 对应的 SRT 字幕文件
```

SRT 文件包含每帧的：
- GPS: 23.183797°N, 113.418708°E
- 相对高度: ~14.6m
- ISO: 400, 快门: 1/800
