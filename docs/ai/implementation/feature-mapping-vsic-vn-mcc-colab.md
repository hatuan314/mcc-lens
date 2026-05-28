---
phase: implementation
title: Implementation Guide — Mapping VSIC VN to MCC on Colab
description: Hướng dẫn triển khai chạy Colab GPU + Ollama, output lên Google Drive
---

# Implementation Guide

## Development Setup

- **Google Colab**: Cần runtime GPU (T4, L4, hoặc A100).
- **Ollama**: Cài đặt trực tiếp trong runtime Colab.
- **Models**: `qwen3.5:9b` (LLM) và `bge-m3` (Embedding).
- **Storage**: Google Drive mount tại `/content/drive`.

## Code Structure

- `main.py`: Bổ sung flag `--gdrive-output-dir`.
- `app/controllers/mapping_controller.py`: Xử lý logic tự động cấu hình đường dẫn khi dùng Drive.
- `colab/mapping_vsic_mcc_colab.ipynb`: Notebook orchestration cho môi trường Colab.

## Implementation Notes

### Core Features

#### Google Drive Output Integration
Khi sử dụng flag `--gdrive-output-dir`, controller sẽ:
1. Tạo thư mục nếu chưa tồn tại.
2. Thiết lập `output` thành `vsic-mcc-mapping.xlsx`.
3. Thiết lập `output_detail` thành `vsic-mcc-mapping-detail.xlsx`.
4. Thiết lập `checkpoint_path` thành `.mapping-progress.json`.

Điều này giúp người dùng Colab không cần phải truyền quá nhiều đường dẫn dài dòng.

#### Checkpoint & Resume
Sử dụng `MappingCheckpointRepository` để lưu trạng thái sau mỗi bản ghi VSIC. File checkpoint được lưu trên Drive đảm bảo có thể resume ngay cả khi Colab bị ngắt kết nối hoặc reset runtime.

## Error Handling

- **Drive not mounted**: Báo lỗi nếu đường dẫn `/content/drive` không truy cập được.
- **Ollama connection**: Kiểm tra health check trước khi chạy.
- **VRAM issues**: Nếu dùng model quá lớn trên GPU yếu, có thể gây crash. `qwen3.5:9b` được chọn vì phù hợp với GPU T4 phổ biến trên Colab.

## Performance Considerations

- **GPU Acceleration**: Ollama tự động sử dụng GPU nếu có.
- **Top-K Filtering**: Giảm số lượng ứng viên MCC gửi vào LLM (mặc định 60) để cân bằng độ chính xác và tốc độ inference.
- **Batching**: Hiện tại xử lý tuần tự từng VSIC để đảm bảo tính ổn định của checkpoint.
