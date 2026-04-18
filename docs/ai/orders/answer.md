### **y_threshold_pct expose qua CLI hay hardcode default?**

**1. Về việc quản lý Y threshold:**

- **Ưu tiên:** Nên **Expose qua CLI (hoặc Config file/Constructor)** thay vì hardcode.
- **Lý do:** \* Tài liệu PDF của mỗi tổ chức (Visa, Mastercard, NAPAS) sẽ có mật độ dòng (line spacing) khác nhau. Việc để threshold là một tham số đầu vào giúp module của tôi có tính **tổng quát hóa (Generalization)** cao, không chỉ dùng cho mỗi tài liệu Visa này.
  - Trong quá trình làm Benchmarking, tôi cần chạy thử nghiệm với nhiều ngưỡng khác nhau (ví dụ: 0.005, 0.01, 0.015) để tìm ra điểm tối ưu (Sweet spot) mà không muốn phải sửa source code liên tục.

**2. Chiến lược triển khai gợi ý:**

- Hãy tạo một class `MCCExtractor` với tham số khởi tạo (init) chứa `y_threshold_pct`.
- Thiết lập **giá trị mặc định (Default)** là `0.01` (1.0%).
- Nếu sử dụng CLI, hãy dùng thư viện `argparse` hoặc `click` để người dùng có thể truyền tham số như: `--y-threshold 0.012`.

**3. Bổ sung về logic Row-grouping:**

- Thay vì chỉ dựa vào một ngưỡng Y duy nhất, bạn có thể cân nhắc sử dụng thuật toán **DBSCAN (Density-Based Spatial Clustering)** đơn giản trên trục Y để tự động nhóm các text có cao độ gần nhau. Nếu không, cách dùng `% threshold` vẫn là lựa chọn an toàn và dễ kiểm soát nhất hiện tại.
