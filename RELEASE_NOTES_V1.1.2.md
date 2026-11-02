## ⏰ Auto Shutdown v1.1.2

Bản vá lỗi cho tính năng **Hẹn giờ bật máy**: máy đã đúng giờ bật lại nhưng **không hiện gì** — không có biểu tượng trong khay hệ thống, không có thông báo.

### 📥 Tải về

| File | Kích thước | Mô tả |
|---|---|---|
| `AutoShutdown.exe` | ~34 MB | File thực thi duy nhất, chạy độc lập, không cần cài Python |

> ⚠️ **Windows SmartScreen:** File không được ký số nên Windows có thể hiện cảnh báo.
> Chọn **Thông tin thêm → Chạy dù sao**.

---

### 🐛 Đã sửa

- 🐛 **Máy bật lại nhưng app chạy ở session 0** — task dùng `LogonType: S4U` nên app khởi chạy trong session 0 (session hệ thống), không có tray icon và không hiện được thông báo "Máy đã tự bật lại". Trông như tính năng không hoạt động.
  Nay dùng lại `LogonType: Interactive` → app chạy đúng session của bạn, thông báo hiện bình thường.
- ✅ **Giữ nguyên việc không bọc `cmd.exe`** — lệnh gọi thẳng file thực thi, không qua `cmd.exe /c` nên không còn lỗi mất dấu nháy.
- ✅ **Giữ nguyên cảnh báo `powercfg /waketimers`** — app vẫn kiểm tra xem Windows có thật sự arm RTC timer hay không, và cảnh báo nếu BIOS chưa bật *Wake on RTC alarm*.

---

### 🔎 Ghi chú kỹ thuật

Đo được trên máy thực tế (ASUS, Realtek 2.5GbE):

| LogonType | RTC alarm được arm? | Session của app | Thông báo |
|---|---|---|---|
| `Interactive` | ✅ Có | 1 (session của bạn) | ✅ Hiện |
| `S4U` | ✅ Có | 0 (session hệ thống) | ❌ Không hiện |

Việc **đánh thức máy** do RTC alarm của BIOS đảm nhiệm và không phụ thuộc `LogonType` — cả hai đều arm được timer. `LogonType` chỉ quyết định **app có chạy trong session của bạn hay không**. Vì vậy `Interactive` là lựa chọn đúng cho tính năng này.

---

### 🔧 Điều kiện để RTC wake hoạt động

Máy của bạn đã đạt đủ:

- ✅ **Wake on RTC alarm** — đã bật trong BIOS
- ✅ **Fast Startup** — đã tắt (`HiberbootEnabled = 0`), đây là điều kiện **bắt buộc**, nếu bật thì Windows không đặt RTC alarm khi tắt máy
- ✅ **Hibernate** — không khả dụng, nên tắt máy là tắt thật (S5)
- ⚠️ **Task Scheduler service** — phải `Running` + `Automatic` (mặc định)

---

### 📖 Cách dùng

1. Chạy `AutoShutdown.exe` với quyền quản trị
2. Vào tab **Hẹn bật máy** → chọn giờ → **Hẹn giờ bật máy**
3. Kiểm tra thông báo:
   - ✅ *"Máy sẽ tự bật lại lúc ..."* → RTC timer đã arm thành công
   - ⚠️ *"Windows chưa bật timer RTC"* → kiểm tra lại *Wake on RTC alarm* trong BIOS
4. Hẹn giờ tắt máy như bình thường — máy sẽ tự bật lại đúng giờ đã chọn

---

### 📄 License

MIT — xem [LICENSE](https://github.com/iamhieuxz/autoshutdown/blob/main/LICENSE).
