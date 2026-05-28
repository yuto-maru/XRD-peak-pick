import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox
import pyperclip


# =========================================================
# USER INPUT
# =========================================================

def input_q_values():
    print("q値をスペース区切りで入力してください")
    print("例: 2.7827 3.3936 3.9638 4.7784 5.5929 5.9594 6.8145 7.0588 7.9138")
    s = input("q_exp = ").strip()
    q = np.array([float(x) for x in s.split()])
    return np.sort(q)


show_labels = True
n_theory_to_print = 60
ring_margin = 0.5
show_lattice_lines = True

initial_gamma_deg = 90.0
gamma_min_deg = 90.0
gamma_max_deg = 170.0

hard_limit_h = 200
hard_limit_k = 200


# =========================================================
# FUNCTIONS
# =========================================================

def calc_ab_oblique_from_q1_q2(q1, q2):
    return q1, q2


def solve_q01_from_second_peak(q1, q2, gamma_deg, h2, k2):
    gamma_draw = np.deg2rad(180.0 - gamma_deg)
    c = np.cos(gamma_draw)

    h2 = int(h2)
    k2 = int(k2)

    if h2 == 0 and k2 == 0:
        raise ValueError("2nd peak の Miller 指数に (0,0) は使えません。")

    if k2 == 0:
        raise ValueError("2nd peak の k が 0 だと b を決められません。")

    A = k2 ** 2
    B = 2.0 * h2 * k2 * q1 * c
    C = (h2 ** 2) * (q1 ** 2) - (q2 ** 2)

    D = B ** 2 - 4.0 * A * C

    if D < -1e-12:
        raise ValueError("この Miller 指数では q2 を再現できません。")

    D = max(D, 0.0)

    roots = [
        (-B + np.sqrt(D)) / (2.0 * A),
        (-B - np.sqrt(D)) / (2.0 * A)
    ]

    positive_roots = [r for r in roots if r > 1e-12]

    if len(positive_roots) == 0:
        raise ValueError("正の |b*| が得られません。")

    if root_mode["data"] == "min":
        chosen = min(positive_roots)
    else:
        chosen = max(positive_roots)

    if verbose["data"]:
        print(
            f"\n候補 q01 = {[round(r, 6) for r in positive_roots]} "
            f"→ 採用 q01 = {chosen:.6f} ({root_mode['data']})"
        )

    return chosen


def direct_a_b_from_q1_q2_gamma(q1, q2, gamma_deg, second_hk=(0, 1)):
    gamma = np.deg2rad(gamma_deg)
    s = np.sin(gamma)

    if s <= 1e-12:
        raise ValueError("gamma が 0° または 180° に近すぎます。")

    h2, k2 = second_hk
    q01 = solve_q01_from_second_peak(q1, q2, gamma_deg, h2, k2)

    a = 2 * np.pi / (q1 * s)
    b = 2 * np.pi / (q01 * s)

    return a, b


def reciprocal_basis(a, b, gamma_deg):
    gamma = np.deg2rad(gamma_deg)
    s = np.sin(gamma)

    if abs(s) < 1e-12:
        raise ValueError("sin(gamma) が小さすぎます。")

    gamma_draw_deg = 180.0 - gamma_deg
    gamma_draw = np.deg2rad(gamma_draw_deg)

    q10 = 2 * np.pi / (a * s)
    q01 = 2 * np.pi / (b * s)

    a_star = np.array([q10, 0.0])

    b_star = np.array([
        q01 * np.cos(gamma_draw),
        q01 * np.sin(gamma_draw)
    ])

    return a_star, b_star


def q_hk_vector(h, k, a, b, gamma_deg):
    a_star, b_star = reciprocal_basis(a, b, gamma_deg)
    return h * a_star + k * b_star


def q_hk(h, k, a, b, gamma_deg):
    vec = q_hk_vector(h, k, a, b, gamma_deg)
    return np.linalg.norm(vec)


def allowed_reflection(h, k):
    return not (h == 0 and k == 0)


def generate_hk_list(h_max=8, k_max=8, include_negative_k=True):
    hk_list = []
    k_min = -k_max if include_negative_k else 0

    for h in range(0, h_max + 1):
        for k in range(k_min, k_max + 1):
            if allowed_reflection(h, k):
                hk_list.append((h, k))

    return hk_list


def theory_peaks(a, b, gamma_deg, hk_list):
    peaks = []

    for h, k in hk_list:
        q = q_hk(h, k, a, b, gamma_deg)
        peaks.append((h, k, q))

    peaks.sort(key=lambda x: x[2])

    return peaks


def auto_hk_max_from_qmax(a, b, gamma_deg, q_exp):
    q_exp_max = float(np.max(q_exp))

    h_max = 1
    while h_max < hard_limit_h:
        if q_hk(h_max, 0, a, b, gamma_deg) > q_exp_max:
            break
        h_max += 1

    k_max = 1
    while k_max < hard_limit_k:
        if q_hk(0, k_max, a, b, gamma_deg) > q_exp_max:
            break
        k_max += 1

    return h_max, k_max


def canonical_hk(h, k):
    if h == 0 and k < 0:
        return h, -k
    return h, k


def overbar_int(n):
    if n >= 0:
        return str(n)

    s = str(abs(n))
    return "".join(ch + "\u0304" for ch in s)


def miller_string(h, k, l=0):
    return f"{overbar_int(h)}{overbar_int(k)}{overbar_int(l)}"


def excel_miller_string(h, k, l=0):
    return miller_string(h, k, l)


def print_theory_table(title, a, b, gamma_deg, peaks, n_print=40):
    gamma_draw_deg = 180.0 - gamma_deg

    print(f"\n=== {title} ===")
    print(f"a = {a:.6f}")
    print(f"b = {b:.6f}")
    print(f"gamma = {gamma_deg:.3f} deg")
    print(f"draw_angle = {gamma_draw_deg:.3f} deg")
    print(" rank    h    k     q_calc")

    shown = set()
    rank = 1

    for h, k, q in peaks:
        h_show, k_show = canonical_hk(h, k)

        key = (h_show, k_show)

        if key in shown:
            continue

        shown.add(key)

        print(f"{rank:>4d}  {h_show:>3d}  {k_show:>3d}   {q:>8.4f}")
        rank += 1

        if rank > n_print:
            break


def nearest_theory_assignments(q_exp, peaks):
    result = []
    q_theory = np.array([p[2] for p in peaks])

    for q in q_exp:
        idx = np.argmin(np.abs(q_theory - q))
        h, k, qcalc = peaks[idx]

        h_show, k_show = canonical_hk(h, k)

        diff = q - qcalc
        rel = diff / q if q != 0 else np.nan

        result.append((q, h_show, k_show, qcalc, diff, rel))

    return result


def print_assignment_table(title, assignments):
    print(f"\n--- {title}: nearest assignments ---")
    print(" q_exp      h    k   q_calc    diff      rel_diff")

    for q, h, k, qcalc, diff, rel in assignments:
        print(
            f"{q:7.3f}   {h:>3d}  {k:>3d}   "
            f"{qcalc:7.3f}   {diff:8.3f}   {rel:9.4f}"
        )


def print_current_gamma_results(a, b, gamma_deg, peaks):
    assignments = nearest_theory_assignments(q_exp, peaks)

    print("\n" + "=" * 70)
    print(f"Current gamma = {gamma_deg:.1f} deg")
    print(f"a = {a:.6f}")
    print(f"b = {b:.6f}")
    print(f"2nd peak assignment = ({second_hk['data'][0]},{second_hk['data'][1]})")
    print(f"root mode = {root_mode['data']}")

    print_theory_table(
        "Theory peaks at current gamma",
        a, b, gamma_deg, peaks,
        n_print=n_theory_to_print
    )

    print_assignment_table(
        f"Nearest assignments at gamma = {gamma_deg:.1f} deg",
        assignments
    )

    print("=" * 70)


def draw_lattice_grid(ax, a, b, gamma_deg, h_max, k_max):
    a_star, b_star = reciprocal_basis(a, b, gamma_deg)

    t_vals = np.linspace(-k_max, k_max, 300)

    for h in range(0, h_max + 1):
        xs = []
        ys = []

        for t in t_vals:
            vec = h * a_star + t * b_star
            xs.append(vec[0])
            ys.append(vec[1])

        ax.plot(xs, ys, linewidth=0.6, alpha=0.25)

    t_vals2 = np.linspace(0, h_max, 300)

    for k in range(-k_max, k_max + 1):
        xs = []
        ys = []

        for t in t_vals2:
            vec = t * a_star + k * b_star
            xs.append(vec[0])
            ys.append(vec[1])

        ax.plot(xs, ys, linewidth=0.6, alpha=0.25)


def build_selected_d_table(selected_hk_set, a, b, gamma_deg):
    table = []

    for h, k in selected_hk_set:
        q = q_hk(h, k, a, b, gamma_deg)
        d = 2 * np.pi / q
        table.append((h, k, d))

    if len(table) == 0:
        return ""

    table.sort(key=lambda x: x[2], reverse=True)
    d_max = max(t[2] for t in table)

    lines = []

    for h, k, d in table:
        miller = excel_miller_string(h, k, 0)
        ratio = d / d_max

        lines.append(
            f"{miller}\t{h}\t{k}\t0\t{d:.6f}\t{ratio:.6f}"
        )

    return "\n".join(lines)


def make_peaks_for_gamma(gamma_deg):
    a, b = direct_a_b_from_q1_q2_gamma(
        q1,
        q2,
        gamma_deg,
        second_hk=second_hk["data"]
    )

    h_max, k_max = auto_hk_max_from_qmax(a, b, gamma_deg, q_exp)

    hk_list = generate_hk_list(
        h_max=h_max,
        k_max=k_max,
        include_negative_k=True
    )

    peaks = theory_peaks(a, b, gamma_deg, hk_list)

    return a, b, h_max, k_max, peaks


# =========================================================
# MAIN
# =========================================================

q_exp = input_q_values()

if len(q_exp) < 2:
    raise ValueError("少なくとも2本のq値が必要です。")

q1, q2 = q_exp[0], q_exp[1]
_ = calc_ab_oblique_from_q1_q2(q1, q2)

gamma_deg = initial_gamma_deg

second_hk = {"data": (0, 1)}
root_mode = {"data": "max"}
verbose = {"data": False}

selected_hk = set()
selected_scatter = [None]

a, b, h_max, k_max, peaks = make_peaks_for_gamma(gamma_deg)

fig, ax = plt.subplots(figsize=(11, 8))
plt.subplots_adjust(bottom=0.20, right=0.78)


def get_toolbar():
    manager = getattr(fig.canvas, "manager", None)

    if manager is None:
        return None

    return getattr(manager, "toolbar", None)


def preserve_view_and_mode(func, *args, **kwargs):
    toolbar = get_toolbar()

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    old_mode = ""

    if toolbar is not None and hasattr(toolbar, "mode"):
        old_mode = toolbar.mode

    func(*args, **kwargs)

    try:
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
    except Exception:
        pass

    if toolbar is not None and hasattr(toolbar, "mode"):
        try:
            if old_mode == "zoom rect" and toolbar.mode != old_mode:
                toolbar.zoom()
            elif old_mode == "pan/zoom" and toolbar.mode != old_mode:
                toolbar.pan()
        except Exception:
            pass

    fig.canvas.draw_idle()


last_peaks = {"data": peaks}
last_a = {"data": a}
last_b = {"data": b}
last_hkmax = {"data": (h_max, k_max)}


def redraw():
    ax.clear()

    a_now, b_now, h_max_use, k_max_use, peaks_now = make_peaks_for_gamma(gamma_deg)

    last_a["data"] = a_now
    last_b["data"] = b_now
    last_hkmax["data"] = (h_max_use, k_max_use)
    last_peaks["data"] = peaks_now

    theta = np.linspace(0, 2 * np.pi, 800)

    for q in q_exp:
        x = q * np.cos(theta)
        y = q * np.sin(theta)
        ax.plot(x, y, linewidth=1)

    if show_lattice_lines:
        draw_lattice_grid(ax, a_now, b_now, gamma_deg, h_max_use, k_max_use)

    qx_vals = []
    qy_vals = []
    used_peaks = []

    for h, k, q in peaks_now:
        vec = q_hk_vector(h, k, a_now, b_now, gamma_deg)
        x, y = vec[0], vec[1]

        if x < -1e-10:
            continue

        qx_vals.append(x)
        qy_vals.append(y)
        used_peaks.append((h, k, q))

    ax.scatter(qx_vals, qy_vals, s=30)

    if show_labels:
        for (h, k, q), x, y in zip(used_peaks, qx_vals, qy_vals):
            label = f"({overbar_int(h)}{overbar_int(k)})"
            ax.text(x + 0.03, y + 0.03, label, fontsize=8)

    if selected_scatter[0] is not None:
        try:
            selected_scatter[0].remove()
        except Exception:
            pass

        selected_scatter[0] = None

    if len(selected_hk) > 0:
        xs = []
        ys = []

        for h, k in selected_hk:
            vec = q_hk_vector(h, k, a_now, b_now, gamma_deg)
            x, y = vec[0], vec[1]

            if x < -1e-10:
                continue

            xs.append(x)
            ys.append(y)

        if len(xs) > 0:
            selected_scatter[0] = ax.scatter(
                xs,
                ys,
                s=100,
                color="red",
                zorder=5
            )

    max_x = max(qx_vals) if len(qx_vals) > 0 else 0
    max_abs_y = max([abs(y) for y in qy_vals], default=0)
    q_max_exp = max(q_exp) if len(q_exp) > 0 else 0

    x_lim = max(max_x, q_max_exp) + ring_margin
    y_lim = max(max_abs_y, q_max_exp) + ring_margin

    gamma_draw_deg = 180.0 - gamma_deg

    ax.set_title(
        f"Oblique columnar\n"
        f"1st=(10), "
        f"2nd=({overbar_int(second_hk['data'][0])}{overbar_int(second_hk['data'][1])}), "
        f"root={root_mode['data']}\n"
        f"a={a_now:.3f}, b={b_now:.3f}, "
        f"gamma={gamma_deg:.1f}°, draw_angle={gamma_draw_deg:.1f}°\n"
        f"h_max={h_max_use}, k_max={k_max_use}"
    )

    ax.set_xlabel("q_x")
    ax.set_ylabel("q_y")

    ax.set_xlim(0, x_lim)
    ax.set_ylim(-y_lim, y_lim)

    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)

    fig.canvas.draw_idle()


def find_nearest_point(x_click, y_click):
    peaks_now = last_peaks["data"]

    if peaks_now is None:
        return None, np.inf

    a_now = last_a["data"]
    b_now = last_b["data"]

    min_dist = np.inf
    nearest = None

    for h, k, q in peaks_now:
        vec = q_hk_vector(h, k, a_now, b_now, gamma_deg)
        x = vec[0]
        y = vec[1]

        if x < -1e-10:
            continue

        dist = (x - x_click) ** 2 + (y - y_click) ** 2

        if dist < min_dist:
            min_dist = dist
            nearest = (h, k)

    return nearest, min_dist


def on_click(event):
    toolbar = get_toolbar()

    if toolbar is not None and hasattr(toolbar, "mode"):
        if toolbar.mode in ["zoom rect", "pan/zoom"]:
            return

    if event.inaxes != ax:
        return

    if event.xdata is None or event.ydata is None:
        return

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    if event.button == 3:
        selected_hk.clear()
        redraw()
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        fig.canvas.draw_idle()
        return

    if event.button != 1:
        return

    nearest, min_dist = find_nearest_point(event.xdata, event.ydata)

    if nearest is None:
        return

    x_range = ax.get_xlim()[1] - ax.get_xlim()[0]
    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
    threshold = (0.03 * max(x_range, y_range)) ** 2

    if min_dist > threshold:
        return

    if nearest in selected_hk:
        selected_hk.remove(nearest)
    else:
        selected_hk.add(nearest)

    redraw()

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    fig.canvas.draw_idle()


def on_key(event):
    if event.key is None:
        return

    if event.key.lower() != "c":
        return

    if len(selected_hk) == 0:
        return

    a_now = last_a["data"]
    b_now = last_b["data"]

    text = build_selected_d_table(selected_hk, a_now, b_now, gamma_deg)

    pyperclip.copy(text)

    print("\n選択点をクリップボードにコピーしました")
    print("形式: miller / h / k / l / d / d_over_dmax")
    print(text)
    print()


def update_gamma(delta):
    global gamma_deg

    def _inner():
        global gamma_deg

        gamma_deg += delta

        if gamma_deg < gamma_min_deg:
            gamma_deg = gamma_min_deg

        if gamma_deg > gamma_max_deg:
            gamma_deg = gamma_max_deg

        gamma_deg = round(gamma_deg, 1)

        redraw()

    preserve_view_and_mode(_inner)


def reset_gamma(event):
    global gamma_deg

    def _inner():
        global gamma_deg
        gamma_deg = initial_gamma_deg
        redraw()

    preserve_view_and_mode(_inner)


def on_print(event):
    verbose["data"] = True

    try:
        a_now, b_now, h_max_now, k_max_now, peaks_now = make_peaks_for_gamma(gamma_deg)

        last_a["data"] = a_now
        last_b["data"] = b_now
        last_hkmax["data"] = (h_max_now, k_max_now)
        last_peaks["data"] = peaks_now

        print_current_gamma_results(a_now, b_now, gamma_deg, peaks_now)

    finally:
        verbose["data"] = False


def on_auto_select_nearest(event):
    def _inner():
        peaks_now = last_peaks["data"]

        if peaks_now is None:
            print("まだデータがありません")
            return

        assignments = nearest_theory_assignments(q_exp, peaks_now)

        selected_hk.clear()

        for q, h_show, k_show, qcalc, diff, rel in assignments:
            selected_hk.add((h_show, k_show))

        redraw()

    preserve_view_and_mode(_inner)


def toggle_root(event):
    def _inner():
        if root_mode["data"] == "max":
            root_mode["data"] = "min"
            btn_root.label.set_text("root: min")
        else:
            root_mode["data"] = "max"
            btn_root.label.set_text("root: max")

        selected_hk.clear()
        redraw()

    preserve_view_and_mode(_inner)


def parse_hk_text(text):
    text = text.strip().replace(",", " ")

    if len(text) == 0:
        raise ValueError("Miller 指数を入力してください。例: 0 1")

    parts = text.split()

    if len(parts) == 2:
        h = int(parts[0])
        k = int(parts[1])

    elif len(parts) == 1 and parts[0].lstrip("-").isdigit() and len(parts[0]) == 2:
        h = int(parts[0][0])
        k = int(parts[0][1])

    else:
        raise ValueError("入力形式は '0 1' や '1 1' のようにしてください。")

    if h == 0 and k == 0:
        raise ValueError("(0,0) は使えません。")

    if k == 0:
        raise ValueError("k=0 では b が決められません。例: 0 1, 1 1, 0 2")

    return h, k


def apply_second_hk(event=None):
    def _inner():
        text = text_second_hk.text

        try:
            hk = parse_hk_text(text)

            direct_a_b_from_q1_q2_gamma(
                q1,
                q2,
                gamma_deg,
                second_hk=hk
            )

        except Exception as e:
            print(f"2nd peak の指数を変更できません: {e}")
            return

        second_hk["data"] = hk
        selected_hk.clear()
        redraw()

    preserve_view_and_mode(_inner)


# =========================================================
# BUTTONS
# =========================================================

ax_gm1 = plt.axes([0.05, 0.04, 0.08, 0.06])
ax_gp1 = plt.axes([0.15, 0.04, 0.08, 0.06])
ax_gm01 = plt.axes([0.25, 0.04, 0.08, 0.06])
ax_gp01 = plt.axes([0.35, 0.04, 0.08, 0.06])
ax_reset = plt.axes([0.45, 0.04, 0.08, 0.06])
ax_print = plt.axes([0.58, 0.04, 0.10, 0.06])
ax_auto = plt.axes([0.72, 0.04, 0.13, 0.06])

ax_hkbox = plt.axes([0.82, 0.68, 0.14, 0.05])
ax_hkapply = plt.axes([0.82, 0.60, 0.14, 0.055])
ax_root = plt.axes([0.82, 0.50, 0.14, 0.055])

btn_gm1 = Button(ax_gm1, "-1°")
btn_gp1 = Button(ax_gp1, "+1°")
btn_gm01 = Button(ax_gm01, "-0.1°")
btn_gp01 = Button(ax_gp01, "+0.1°")
btn_reset = Button(ax_reset, "Reset")
btn_print = Button(ax_print, "Print")
btn_auto = Button(ax_auto, "Auto select")

text_second_hk = TextBox(ax_hkbox, "2nd hk", initial="0 1")

btn_hkapply = Button(ax_hkapply, "Apply hk")
btn_root = Button(ax_root, "root: max")

btn_gm1.on_clicked(lambda event: update_gamma(-1.0))
btn_gp1.on_clicked(lambda event: update_gamma(+1.0))
btn_gm01.on_clicked(lambda event: update_gamma(-0.1))
btn_gp01.on_clicked(lambda event: update_gamma(+0.1))
btn_reset.on_clicked(reset_gamma)
btn_print.on_clicked(on_print)
btn_auto.on_clicked(on_auto_select_nearest)
btn_hkapply.on_clicked(apply_second_hk)
text_second_hk.on_submit(apply_second_hk)
btn_root.on_clicked(toggle_root)

fig.canvas.mpl_connect("button_press_event", on_click)
fig.canvas.mpl_connect("key_press_event", on_key)


# =========================================================
# INITIAL DISPLAY
# =========================================================

print("\nExperimental q values:")

for i, q in enumerate(q_exp, start=1):
    print(f"{i:>2d}: {q:.4f}")

print("\n初期表示しました。")
print("角度を変えても自動では print しません。")
print("2nd hk に例: 0 1 / 1 1 / 0 2 を入力して Apply hk を押すと、2nd peak の指数を変更して再計算します。")
print("root: max/min ボタンで、q01 の2つの正の解のどちらを使うか切り替えられます。")
print("現在の角度で理論値を出す場合は Print ボタンを押してください。")
print("点を選択して c キーを押すと、miller / h / k / l / d / d_over_dmax をコピーします。")
print("miller の先頭に ' は付きません。")

redraw()
plt.show()
