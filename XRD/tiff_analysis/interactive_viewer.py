import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import glob
import os

# ===== tif一覧 =====
tif_files = glob.glob("*.tif")

if len(tif_files) == 0:
    print("No tif files found.")
    exit()

print("Available tif files:")
for i, f in enumerate(tif_files):
    print(f"{i}: {f}")

index = int(input("Select file number: "))
image_path = tif_files[index]

print("Loading:", image_path)

# ===== 読み込み =====
img = Image.open(image_path)
img_array = np.array(img).astype(np.float32)

# ===== 初期設定 =====
init_low = 1
init_high = 99
use_log = False

fig, ax = plt.subplots()
plt.subplots_adjust(bottom=0.35)

# ----- スライダーを先に作る -----
ax_low = plt.axes([0.15, 0.22, 0.65, 0.03])
ax_high = plt.axes([0.15, 0.17, 0.65, 0.03])

slider_low = Slider(ax_low, "Low %", 0, 50, valinit=init_low)
slider_high = Slider(ax_high, "High %", 50, 100, valinit=init_high)

# ----- 処理関数 -----
def process_image():
    data = img_array.copy()

    if use_log:
        # ★ 負値・ゼロ対策（超重要）
        data = np.clip(data, 0, None)

        # ★ 安全なオフセット
        offset = np.percentile(data[data > 0], 1) if np.any(data > 0) else 1

        data = np.log10(data + offset)

    vmin = np.percentile(data, slider_low.val)
    vmax = np.percentile(data, slider_high.val)

    # ★ NaN対策
    if not np.isfinite(vmin):
        vmin = np.nanmin(data)
    if not np.isfinite(vmax):
        vmax = np.nanmax(data)

    if vmax <= vmin:
        vmax = vmin + 1e-6

    result = (data - vmin) / (vmax - vmin)
    result = np.clip(result, 0, 1)

    return result

# ----- 初期表示 -----
im = ax.imshow(process_image(), vmin=0, vmax=1)
plt.colorbar(im)
ax.set_title("LINEAR")

# ----- ボタン -----
ax_toggle = plt.axes([0.25, 0.08, 0.2, 0.06])
ax_save = plt.axes([0.55, 0.08, 0.2, 0.06])

button_toggle = Button(ax_toggle, "Linear/Log")
button_save = Button(ax_save, "Save")

# ----- 更新 -----
def update(val):
    im.set_data(process_image())
    fig.canvas.draw_idle()

def toggle_scale(event):
    global use_log
    use_log = not use_log
    ax.set_title("LOG" if use_log else "LINEAR")
    update(None)

def save_image(event):
    processed = process_image()
    save_data = (processed * 65535).astype(np.uint16)

    base, _ = os.path.splitext(image_path)
    scale_type = "log" if use_log else "linear"
    filename = f"{base}_{scale_type}_{int(slider_low.val)}-{int(slider_high.val)}.tif"

    Image.fromarray(save_data).save(filename)
    print("Saved:", filename)

slider_low.on_changed(update)
slider_high.on_changed(update)
button_toggle.on_clicked(toggle_scale)
button_save.on_clicked(save_image)

plt.show()
