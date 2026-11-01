## ⏰ Auto Shutdown v1.1.0

Bản cập nhật bổ sung **tính năng tự thu gọn** cho pop-up đếm ngược — pop-up giờ tự chui vào mép màn hình khi bạn không dùng đến, không còn vướng vào công việc đang mở.

### 📥 Tải về

| File | Kích thước | Mô tả |
|---|---|---|
| `AutoShutdown.exe` | ~34 MB | File thực thi duy nhất, chạy độc lập, không cần cài Python |

> ⚠️ **Windows SmartScreen:** File không được ký số nên Windows có thể hiện cảnh báo.
> Chọn **Thông tin thêm → Chạy dù sao**.

---

### ✨ Mới trong v1.1.0

- 🔘 **Tự thu gọn sau 30 giây** — không rê chuột vào pop-up đếm ngược trong 30 giây, panel tự thu nhỏ lại thành vòng tròn nhỏ chui vào mép màn hình (trái hoặc phải, tùy vị trí panel).
- ⭕ **Chỉ lộ 1/3 vòng tròn** — phần còn lại nẩy khuất ngoài màn hình, chỉ hiện đúng 29/84 px.
- 📊 **Vòng cung tiến trình** — vòng tròn hiển thị vòng cung màu cyan tiến trình đã đi, ở giữa là thời gian còn lại dạng rút gọn (`1h02`, `05:30`).
- 🖱️ **Rê chuột là hiện lại** — di chuột vào vòng tròn, pop-up đầy đủ hiện trở lại ngay lập tức.
- 📍 **Không nhảy vị trí** — vòng tròn giữ nguyên chiều dọc của panel nên không nhảy khi thu gọn.

### 🐛 Sửa lỗi từ v1.0.0

- Mũi tên tăng/giảm trên ô chọn giờ giờ vẽ bằng `QPainter` nên luôn sắc nét, đúng hình — trước đây pseudo-element `::up-arrow` của `QTimeEdit` bị Qt vẽ đè thành vạch ngang.
- Bỏ thanh progress bar khỏi pop-up đếm ngược, thu gọn chiều cao panel từ 214px xuống 172px.
- Pop-up đếm ngược tự chọn mép màn hình gần nhất khi thu gọn thay vì góc cố định.

---

### 📋 Tính năng đầy đủ

- 🕐 **Hẹn giờ tắt máy** — chọn giờ, tự động đếm ngược, tự xử lý qua nửa đêm
- 🔌 **Đóng cổng mạng** — đóng toàn bộ cổng đang mở trước khi tắt máy
- ⏰ **Hẹn giờ bật máy** — máy tự bật lại đúng giờ dù đã tắt hoàn toàn (Wake on RTC)
- 🎨 **Flip-clock đếm ngược** — hiệu ứng lật từng chữ số
- 🎚️ **Độ trong suốt** — chỉnh 30%–100%, vị trí kéo thả được ghi nhớ
- 🖥️ **Chạy ẩn** — không chiếm taskbar, gọn trong system tray

---

### 🛡️ An toàn

Ứng dụng **không bao giờ** đóng tiến trình hệ thống. Bảo vệ gồm 4 lớp:

1. Tiến trình lõi Windows (`PID ≤ 4`)
2. Danh sách tên bảo vệ (`csrss`, `winlogon`, `lsass`, `svchost`, `dwm`...)
3. Mọi tiến trình nằm trong `C:\Windows`
4. Cổng hệ thống (`135`, `445`, `5985`...)

---

### 📖 Hướng dẫn nhanh

1. Chạy `AutoShutdown.exe` → icon xuất hiện trong system tray
2. Click vào icon để mở giao diện
3. Chọn giờ tắt → bấm **Đặt lịch tắt máy**
4. Pop-up flip-clock hiện ở góc dưới bên phải, kéo được, chỉnh độ trong suốt bằng ⚙
5. Không dùng 30s → pop-up tự thu vào mép màn hình, rê chuột vào vòng tròn để mở lại

> Nếu giờ đã qua so với hiện tại, lịch tự được đặt cho ngày hôm sau.

---

### 📋 Yêu cầu hệ thống

- Windows 10 / 11 (64-bit)
- Khuyến nghị chạy với **quyền quản trị** (Run as administrator)
- Tính năng *Hẹn giờ bật máy* cần bật **Wake on RTC** trong BIOS/UEFI

---

### 🔐 Checksum

```
SHA256: (xem tại trang download asset)
```

---

### 📄 License

MIT — xem [LICENSE](https://github.com/iamhieuxz/autoshutdown/blob/main/LICENSE).
