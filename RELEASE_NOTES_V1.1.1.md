## ⏰ Auto Shutdown v1.1.1

Bản vá lỗi cho tính năng **Hẹn giờ bật máy** — máy đã hẹn đúng giờ nhưng không tự bật lại.

### 📥 Tải về

| File | Kích thước | Mô tả |
|---|---|---|
| `AutoShutdown.exe` | ~34 MB | File thực thi duy nhất, chạy độc lập, không cần cài Python |

> ⚠️ **Windows SmartScreen:** File không được ký số nên Windows có thể hiện cảnh báo.
> Chọn **Thông tin thêm → Chạy dù sao**.

---

### 🐛 Đã sửa

- 🐛 **Task bật máy không bao giờ chạy** — lệnh được bọc trong `cmd.exe /c`, cmd.exe bẻ mất dấu nhạy nên Task Scheduler báo lỗi `LastTaskResult: 1`. Nay gọi thẳng file thực thi, không qua `cmd.exe`.
- 🐛 **Task không chạy khi chưa ai đăng nhập** — đổi `LogonType` từ `Interactive` sang `S4U`. Đây là điểm mấu chốt: sau khi máy bật từ RTC alarm thì chưa có phiên đăng nhập nào, task `Interactive` sẽ đứng im cho tới khi bạn đăng nhập thủ công.
- 🐛 **Thời gian hiển thị dạng thô** — trước đây hiện `2026-11-02T23:30:00+07:00`, nay hiện `02/11/2026 23:30`.
- ✨ **Báo cáo trạng thái thật** — sau khi hẹn, app kiểm tra `powercfg /waketimers`. Nếu Windows chưa arm RTC timer thì hiện cảnh báo yêu cầu bật *Wake on RTC alarm* trong BIOS thay vì báo "thành công" một cách giả tạo.

---

### 🔎 Nguyên nhân gốc

Task Scheduler đăng ký RTC alarm đúng, nhưng **action của task** không bao giờ chạy được:

```
LogonType : InteractiveToken   → chờ ai đó đăng nhập mới chạy
Action    : cmd.exe /c "...python.exe" "...AutoShutdown.py" --woke
                         ↑ cmd.exe bẻ ngoặc kép, lệnh hỏng
```

Task Scheduler vẫn đánh thức máy (RTC timer có trong `powercfg /waketimers`), nhưng app không chạy được nên bạn không thấy thông báo "Máy đã tự bật lại".

---

### 📋 Yêu cầu hệ thống

- Windows 10 / 11 (64-bit)
- **Bắt buộc** bật **Wake on RTC alarm** trong BIOS/UEFI (mục *Power Management* / *Alarm Clock*)
- Chạy app với **quyền quản trị**
- Tính năng *Hẹn giờ bật máy* không hoạt động nếu đang bật **Fast Startup** — hãy tắt nó:
  ```
  powercfg /h off
  ```

---

### 📖 Cách dùng

1. Chạy `AutoShutdown.exe` với quyền quản trị
2. Vào tab **Hẹn bật máy** → chọn giờ → **Hẹn giờ bật máy**
3. Kiểm tra thông báo:
   - ✅ *"Máy sẽ tự bật lại lúc ..."* → RTC timer đã arm thành công
   - ⚠️ *"Windows chưa bật timer RTC"* → cần bật Wake on RTC alarm trong BIOS
4. Hẹn giờ tắt máy như bình thường — máy sẽ tự bật lại đúng giờ đã chọn

---

### 📄 License

MIT — xem [LICENSE](https://github.com/iamhieuxz/autoshutdown/blob/main/LICENSE).
