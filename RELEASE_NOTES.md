## ⏰ Auto Shutdown v1.0.0

Công cụ hẹn giờ tắt máy Windows — **nhẹ**, **chạy ẩn** trong system tray, giao diện dark theme với đồng hồ đếm ngược kiểu flip-clock.

### 📥 Tải về

| File | Kích thước | Mô tả |
|---|---|---|
| `AutoShutdown.exe` | ~34 MB | File thực thi duy nhất, chạy độc lập, không cần cài Python |

> ⚠️ **Windows SmartScreen:** File không được ký số nên Windows có thể hiện cảnh báo.
> Chọn **Thông tin thêm → Chạy dù sao**.

---

### ✨ Tính năng

- 🕐 **Hẹn giờ tắt máy** — chọn giờ, tự động đếm ngược, tự xử lý qua nửa đêm
- 🔌 **Đóng cổng mạng** — đóng toàn bộ cổng đang mở trước khi tắt máy
- ⏰ **Hẹn giờ bật máy** — máy tự bật lại đúng giờ dù đã tắt hoàn toàn (Wake on RTC)
- 🎨 **Flip-clock đếm ngược** — hiệu ứng lật từng chữ số, neo góc dưới bên phải
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

> Nếu giờ đã qua so với hiện tại, lịch tự được đặt cho ngày hôm sau.

---

### 📋 Yêu cầu hệ thống

- Windows 10 / 11 (64-bit)
- Khuyến nghị chạy với **quyền quản trị** (Run as administrator)
- Tính năng *Hẹn giờ bật máy* cần bật **Wake on RTC** trong BIOS/UEFI

---

### 🔐 Checksum

```
SHA256: 2B68954554F89A75BFADC7A7E819EA7D00010E2770B7C0047E77F4066AEF7FD1
```

---

### 📄 License

MIT — xem [LICENSE](https://github.com/iamhieuxz/autoshutdown/blob/main/LICENSE).
