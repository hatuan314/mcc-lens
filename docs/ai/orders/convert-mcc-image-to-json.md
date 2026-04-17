# Tính năng convert MCC image to JSON

Trong '/Users/tuanha15/Work/projects/AI/convert-vsic-to-mcc/mcc-lens/assets/mcc-visa' chứa danh sách các mã MCC mà tổ chức VISA cung cấp. Tôi cần convert các file image này thành JSON.
1. Tôi mong muốn sử dụng Florence-2 bản large để convert image thành JSON.
2. Nội dung json gồm các field sau:
- mcc_code: mã MCC
- title: tiêu đề MCC
- description: mô tả MCC
- similar_merchants: danh sách các merchant tương tự
3. Có giao diện CLI loading bar để hiển thị quá trình convert