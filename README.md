<div align="center">

# ⏰ Auto Shutdown

**Công cụ hẹn giờ tắt máy Windows — nhẹ, chạy ẩn, giao diện đẹp.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15-41CD52?logo=qt&logoColor=white)](https://pypi.org/project/PyQt5/)
[![Release](https://img.shields.io/github/v/release/iamhieuxz/autoshutdown?label=Download&color=22C55E)](https://github.com/iamhieuxz/autoshutdown/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-22C55E)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows)](https://www.microsoft.com/windows)

</div>

---

## ✨ Tính năng

| | Tính năng | Mô tả |
|---|---|---|
| 🕐 | **Hẹn giờ tắt máy** | Chọn giờ tắt, tự động đếm ngược. Dòng xem trước cho biết ngay **hôm nay hay ngày mai** và còn bao lâu. Tự xử lý qua nửa đêm (đặt 02:30 lúc 22:20 → tắt lúc 02:30 hôm sau). |
| 🔌 | **Đóng cổng mạng** | Đóng toàn bộ cổng đang mở trước khi tắt máy. Danh sách chia nhóm **ứng dụng** / **hệ thống được bảo vệ** cho dễ đọc, và có hộp xác nhận trước khi đóng. |
| ⏰ | **Hẹn giờ bật máy** | Task Scheduler với `WakeToRun` — máy tự bật lại đúng giờ dù đã tắt hoàn toàn. Chip trạng thái kiểm tra đúng cờ `WakeToRun` của task. |
| 🎨 | **Flip-clock đếm ngược** | Pop-up đồng hồ lật từng chữ số, neo ở góc dưới bên phải, kéo thả được. Có thanh tiến trình chạy hết lịch. |
| 🔘 | **Tự thu gọn** | Không rê chuột 30s → panel thu vào mép màn hình, chỉ lộ 1/3 vòng tròn. Rê chuột vào là hiện lại. |
| 🎚️ | **Độ trong suốt** | Chỉnh 30%–100% cho pop-up đếm ngược, vị trí được ghi nhớ. |
| ⌨️ | **Bàn phím & trợ năng** | Ô giờ chỉnh được bằng **↑/↓** và **←/→** (không cần chuột), mọi nút đều có focus ring, checkbox có dấu ✓ thật (không chỉ đổi màu), icon vẽ vector nên luôn sắc nét. |
| 🖥️ | **Chạy ẩn** | Nằm gọn trong system tray, không chiếm taskbar. Mở lần thứ hai sẽ không tạo thêm bản chạy. |

---

## 📸 Giao diện

<div align="center">

### Lịch tắt máy

<img src="docs/screenshot-schedule.png" alt="Giao diện hẹn giờ tắt máy" width="420">

### Đóng cổng mạng

<img src="docs/screenshot-ports.png" alt="Giao diện đóng cổng mạng" width="420">

### Đếm ngược flip-clock

<img src="docs/screenshot-countdown.png" alt="Pop-up đếm ngược" width="320">

### Tự thu gọn vào mép màn hình

<img src="docs/screenshot-peek.png" alt="Vòng tròn thu gọn ở mép màn hình" width="120">

</div>

---

## 🚀 Cài đặt

## 📥 Tải về

<div align="center">

[![Release](https://img.shields.io/github/v/release/iamhieuxz/autoshutdown?label=Latest&color=22C55E&style=for-the-badge)](https://github.com/iamhieuxz/autoshutdown/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/iamhieuxz/autoshutdown/total?label=Downloads&color=0078D4&style=for-the-badge)](https://github.com/iamhieuxz/autoshutdown/releases)

</div>

### Cách 1: Tải file `.exe` (khuyến nghị)

1. Tải `AutoShutdown.exe` từ mục [Releases](https://github.com/iamhieuxz/autoshutdown/releases).
2. Copy ra Desktop và chạy.

> **Lưu ý:** Windows có thể hiện cảnh báo SmartScreen vì file không được ký số.
> Chọn **Thông tin thêm → Chạy dù sao**.

### Cách 2: Chạy từ mã nguồn

```bash
# Clone repository
git clone https://github.com/iamhieuxz/autoshutdown.git
cd autoshutdown

# Cài dependencies
pip install -r requirements.txt

# Chạy ứng dụng
python AutoShutdown.py
```

### Cách 3: Tự build

```bash
build.bat
```

File `.exe` sẽ nằm trong thư mục `dist/`.

---

## 📖 Hướng dẫn sử dụng

### Khởi động

Ứng dụng chạy ẩn trong **system tray** (góc phải thanh taskbar). Có thể ẩn icon trong khoảng `^`.

### Mở giao diện

- **Click đơn** hoặc **double-click** vào icon trong system tray, hoặc
- Chuột phải → **Đặt lịch tắt máy**

### Đặt lịch tắt máy

1. Chọn tab **Lịch tắt máy**. Giờ mặc định là **30 phút sau** (đổi tuỳ ý).
2. Bấm vào phần **giờ** hoặc **phút** trên ô thời gian để chọn trường cần chỉnh.
3. Dùng mũi tên ▲▼ để điều chỉnh. Giờ vòng `0→23→0`, phút vòng `0→59→0`.
4. (Tùy chọn) Tick **"Đóng tất cả cổng ứng dụng đang mở trước khi tắt máy"**.
5. Bấm **Đặt lịch tắt máy**.

> Nếu giờ đã qua so với thời điểm hiện tại, lịch sẽ tự được đặt cho ngày hôm sau.
> Nếu Windows từ chối lệnh tắt máy, app hiện hộp thoại kèm mã lỗi (thường là mã 5 —
> chạy app bằng quyền quản trị) thay vì đóng im lặng.

### Pop-up đếm ngược

Sau khi đặt lịch, một pop-up flip-clock xuất hiện ở **góc dưới bên phải**:

- **Kéo** để di chuyển — vị trí được ghi nhớ lại.
- **⚙** để chỉnh độ trong suốt.
- **Hủy** để hủy lịch tắt máy ngay lập tức.

#### Tự thu gọn khi không dùng

Nếu bạn không rê chuột vào pop-up trong **30 giây**, panel tự thu nhỏ thành một **vòng tròn nhỏ** chui vào mép màn hình (trái hoặc phải, tùy vị trí hiện tại):

- Chỉ **1/3 vòng tròn** hiện ra, phần còn lại nằm khuất ngoài màn hình.
- Vòng cung màu cyan hiển thị tiến trình, giữa vòng tròn là thời gian còn lại dạng rút gọn (`1h02`, `05:30`).
- **Rê chuột vào vòng tròn** → pop-up đầy đủ hiện lại ngay lập tức.

> Nhờ vậy pop-up không vướng vào công việc đang mở mà thông tin đếm ngược vẫn luôn nhìn thấy được.

### Đóng cổng mạng

Chuyển sang tab **Đóng cổng mạng** để xem toàn bộ cổng đang lắng nghe:

- Cổng **ứng dụng** (màu trắng) → có thể đóng.
- Cổng **hệ thống** (màu xám, ghi lý do bảo vệ) → luôn được bảo vệ.

Bấm **Đóng tất cả cổng ứng dụng** để dọn dẹp ngay — hộp thoại xác nhận sẽ liệt kê các
tiến trình sắp bị đóng — hoặc tick ô trong tab *Lịch tắt máy* để tự động đóng đúng lúc tắt máy.
Mỗi tiến trình chỉ bị đóng **một lần**, dù nó đang giữ nhiều cổng.

### Hẹn giờ bật máy

Chuyển sang tab **Hẹn bật máy**, chọn giờ rồi bấm **Hẹn giờ bật máy**.

Task được đăng ký với tên `AutoShutdown Auto Wake` trong Task Scheduler với các cờ:

| Cờ | Ý nghĩa |
|---|---|
| `WakeToRun` | Bật RTC alarm để đánh thức máy |
| `StartWhenAvailable` | Bật máy ngay cả khi lỡ mất giờ |
| `AllowStartIfOnBatteries` | Cho phép chạy cả khi dùng pin |

> ⚠️ **Yêu cầu:** Bật **Wake on RTC** trong BIOS/UEFI. Đa số mainboard desktop hỗ trợ,
> nhưng một số laptop và máy tính build sẵn không có.

---

## 🔐 An toàn

Ứng dụng **không bao giờ** đóng các tiến trình hệ thống. Cơ chế bảo vệ gồm 5 lớp:

1. **PID ≤ 4** — các tiến trình lõi của Windows.
2. **Danh sách tên bảo vệ** — `csrss`, `wininit`, `winlogon`, `services`, `lsass`, `svchost`, `dwm`, `spoolsv`...
3. **Đường dẫn trong thư mục Windows** — mọi tiến trình nằm trong `C:\Windows` đều được bảo vệ.
4. **Không xác định được tiến trình** — máy nào ẩn tên tiến trình (sandbox, dịch vụ phiên khác) thì cổng đó được coi là **bảo vệ**, không đoán bừa.
5. **Cổng hệ thống** — `53` (DNS), `135`, `137`, `138`, `139`, `445`, `5985`, `5986`, `47001`.

Việc đóng cổng thực hiện bằng `taskkill /F /T` (kill cả tiến trình con) và **hỏi xác nhận trước**.

---

## 🧩 Cấu trúc dự án

```
autoshutdown/
├── AutoShutdown.py        # Điểm vào chính + toàn bộ giao diện Qt
├── port_cleaner.py        # Quét & đóng cổng mạng, logic bảo vệ tiến trình
├── wake_scheduler.py      # Đăng ký Task Scheduler để hẹn giờ bật máy
├── test_port_cleaner.py   # Self-check cho phần quét cổng & bảo vệ tiến trình
├── test_auto_shutdown.py  # Self-check cho phần tính giờ tắt máy & ghi cấu hình
├── test_wake_scheduler.py # Self-check cho phần hẹn giờ bật máy
├── test_app_startup.py    # Self-check dựng toàn bộ app (tray, menu, popup)
├── make_icon.py           # Sinh file icon.ico đa độ phân giải
├── build.bat              # Script build .exe
├── run.bat                # Script chạy nhanh
├── requirements.txt
└── icon.ico
```

Chạy self-check (không cần cài pytest): `python test_app_startup.py` — hoặc `pytest` nếu đã có.

### Design tokens

Toàn bộ giao diện dùng hệ thống token tập trung trong class `Token`:
lưới cách **4px**, bo góc thống nhất (8/12/16/22px), và bảng màu ngữ nghĩa
(`surface`, `border`, `text_primary`, `accent`, `danger`...). Sửa một chỗ là toàn bộ giao diện cập nhật.

---

## 🛠️ Công nghệ

- **Python 3.8+**
- **PyQt5** — framework GUI, vẽ flip-clock bằng `QPainter`
- **psutil** — lấy đường dẫn executable của tiến trình
- **PyInstaller** — đóng gói thành `.exe` chạy độc lập
- **Pillow** — sinh icon đa độ phân giải

---

## ⚙️ Cấu hình

Cài đặt được lưu tại `~/.autoshutdown_settings.json`:

```json
{
  "panel_pos": [749, 465],
  "panel_opacity": 100,
  "open_on_launch": false
}
```

| Khóa | Ý nghĩa |
|---|---|
| `panel_pos` | Vị trí pop-up đếm ngược |
| `popup_pos` | Vị trí cửa sổ chính |
| `panel_opacity` | Độ trong suốt pop-up đếm ngược (30–100) |
| `open_on_launch` | Mở cửa sổ ngay khi khởi động |

File ghi qua temp + `os.replace` nên tắt máy đột ngột giữa lúc lưu không làm hỏng cấu hình.

---

## 📝 Log

Bản `.exe` chạy ẩn nên lỗi được ghi ra file thay vì console:

```
%LOCALAPPDATA%\AutoShutdown\autoshutdown.log
```

Log tự xoay vòng (tối đa 3 file × 500 KB) và ghi lại: đặt/hủy lịch tắt máy, kết quả đóng cổng,
đăng ký lịch bật máy và mọi lỗi không bắt được.

---

## ❓ Khắc phục sự cố

**Không thấy icon trong system tray**
→ Kiểm tra khoảng mũi tên `^` ở góc phải taskbar, hoặc kéo icon ra khỏi vùng ẩn.

**Mở app mà không thấy gì xảy ra**
→ Ứng dụng đã chạy sẵn: chỉ một bản được phép chạy, bản thứ hai sẽ báo và thoát.

**Không đóng được cổng nào**
→ Nhiều cổng thuộc tiến trình hệ thống — đây là hành vi đúng, nhằm tránh làm hỏng Windows.
Tiến trình không xác định được tên cũng được coi là bảo vệ.

**Máy không tự bật lại đúng giờ**
→ Kiểm tra BIOS có bật `Wake on RTC Alarm` / `Resume by RTC Alarm` không. Kiểm tra tại
`Task Scheduler → AutoShutdown Auto Wake → Properties` cờ **Wake the computer to run this task**.
Nếu chip trạng thái báo thiếu `WakeToRun`, hãy xóa lịch rồi đặt lại.

**Windows báo "không thể đặt lịch"**
→ Chạy ứng dụng với quyền quản trị (Run as administrator).

**Cần xem lỗi chi tiết**
→ Mở file log ở mục 📝 Log phía trên.

---

## 📄 License

MIT License — xem [LICENSE](LICENSE).

---

<div align="center">

Made with ☕ using Python & PyQt5

</div>
