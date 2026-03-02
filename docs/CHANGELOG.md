# Changelog

本项目的重要变更记录如下。

## [2026-03-02]

### Added
- 新增 `sampling.only_keyframes` 配置项，支持仅提取关键帧（I 帧 / Intra-coded）。
- 在 PyAV 解码路径中支持关键帧过滤逻辑。

### Changed
- 更新 README 配置文档与功能说明，补充关键帧抽取说明。
- README 新增对本变更记录文件的引用链接。

## [2026-01-30]

### Added
- 支持 DJI SRT 自动检测与解析。
- 支持 GPS（经纬度/高度）写入图像 EXIF（JPEG 输出）。
- 支持 COLMAP GPS 辅助重建工作流。

