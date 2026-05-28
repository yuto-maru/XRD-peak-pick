import numpy as np
import matplotlib.pyplot as plt
import pyperclip
from matplotlib.widgets import Button


# =========================================================
# USER INPUT
# =========================================================

def input_q_values():
    print("q値をスペース区切りで入力してください")
    print("例: 1.89 3.39 3.80 4.33 5.76")
    s = input("q_exp = ").strip()
    q = np.array([float(x) for x in s.split()])
    return np.sort(q)


# Centered rectangular の消滅則 h+k=odd を除くか
use_centering_rule = True

# 点ラベルを表示するか
show_labels = True

# 理論q一覧を何本まで表示するか
n_theory_to_print = 30

# Debye ring 外側の余白
ring_margin = 0.5

# ミラー指数ごとの格子線を描くか
show_lattice_lines = True


# =========================================================
# FUNCTIONS
# =========================================================

def calc_ab_pattern_A(q1, q2):
    """
    Centered rectangular A:
    1st peak = (110) = q1
    2nd peak = (200) = q2
    """
    a = 4 * np.pi / q2
    inside = q1**2 - (2 * np.pi / a) ** 2
    if inside <= 0:
        raise ValueError("Pattern A: b が実数になりません。")
    b = 2 * np.pi / np.sqrt(inside)
    return a, b


def calc_ab_pattern_B(q1, q2):
    """
    Centered rectangular B:
    1st peak = (200) = q1
    2nd peak = (110) = q2
    """
    a = 4 * np.pi / q1
    inside = q2**2 - (2 * np.pi / a) ** 2
    if inside <= 0:
        raise ValueError("Pattern B: b が実数になりません。")
    b = 2 * np.pi / np.sqrt(inside)
    return a, b


def calc_ab_pattern_P2m(q1, q2):
    """
    P2m (primitive rectangular):
    1st peak = (10) = q1
    2nd peak = (01) = q2
    """
    a = 2 * np.pi / q1
    b = 2 * np.pi / q2
    return a, b


def q_hk(h, k, a, b):
    return np.sqrt((2 * np.pi * h / a) ** 2 + (2 * np.pi * k / b) ** 2)


def q_hk_x(h, a):
    return 2 * np.pi * h / a


def q_hk_y(k, b):
    return 2 * np.pi * k / b


def allowed_reflection(h, k, centered=False, use_centering_rule=True):
    if h == 0 and k == 0:
        return False
    if centered and use_centering_rule and ((h + k) % 2 != 0):
        return False
    return True


def generate_hk_list(h_max=8, k_max=8, centered=False, use_centering_rule=True):
    hk_list = []
    for h in range(h_max + 1):
        for k in range(k_max + 1):
            if allowed_reflection(h, k, centered=centered, use_centering_rule=use_centering_rule):
                hk_list.append((h, k))
    return hk_list


def theory_peaks(a, b, hk_list):
    peaks = []
    for h, k in hk_list:
        q = q_hk(h, k, a, b)
        peaks.append((h, k, q))
    peaks.sort(key=lambda x: x[2])
    return peaks


def auto_hk_max_from_qmax(a, b, q_exp):
    """
    実測最大qより大きい (h0) と (0k) が
    それぞれ1個だけ入るように h_max, k_max を決める
    """
    q_exp_max = np.max(q_exp)
    h_max = int(np.floor(q_exp_max * a / (2 * np.pi))) + 1
    k_max = int(np.floor(q_exp_max * b / (2 * np.pi))) + 1
    return h_max, k_max


def print_theory_table(title, a, b, peaks, n_print=30):
    print(f"\n=== {title} ===")
    print(f"a = {a:.6f}")
    print(f"b = {b:.6f}")
    print(" rank   h   k     q_calc")
    for i, (h, k, q) in enumerate(peaks[:n_print], start=1):
        print(f"{i:>4d}  {h:>2d}  {k:>2d}   {q:>8.4f}")


def nearest_theory_assignments(q_exp, peaks):
    result = []
    q_theory = np.array([p[2] for p in peaks])

    for q in q_exp:
        idx = np.argmin(np.abs(q_theory - q))
        h, k, qcalc = peaks[idx]
        diff = q - qcalc
        rel = diff / q if q != 0 else np.nan
        result.append((q, h, k, qcalc, diff, rel))
    return result


def print_assignment_table(title, assignments):
    print(f"\n--- {title}: nearest assignments ---")
    print(" q_exp    h   k   q_calc    diff      rel_diff")
    for q, h, k, qcalc, diff, rel in assignments:
        print(f"{q:6.2f}   {h:>2d}  {k:>2d}   {qcalc:7.3f}   {diff:8.3f}   {rel:9.4f}")


def draw_lattice_grid(ax, a, b, h_max, k_max):
    a_star = 2 * np.pi / a
    b_star = 2 * np.pi / b

    for h in range(h_max + 1):
        x = h * a_star
        ax.axvline(x=x, linewidth=0.8, alpha=0.35)

    for k in range(k_max + 1):
        y = k * b_star
        ax.axhline(y=y, linewidth=0.8, alpha=0.35)


def build_selected_d_table(selected_hk_set, a, b):
    """
    選択点だけを d の大きい順に並べて
    Excel貼り付け用TSV文字列を返す

    1列目: miller
    2列目: h
    3列目: k
    4列目: l (=0)
    5列目: d
    6列目: d/d_max
    """
    table = []

    for h, k in selected_hk_set:
        q = q_hk(h, k, a, b)
        d = 2 * np.pi / q
        table.append((h, k, d))

    if len(table) == 0:
        return ""

    table.sort(key=lambda x: x[2], reverse=True)  # dが大きい順
    d_max = max(t[2] for t in table)

    lines = []
    for h, k, d in table:
        miller = f"{h}{k}0"
        ratio = d / d_max
        lines.append(f"{miller}\t{h}\t{k}\t0\t{d:.6f}\t{ratio:.6f}")

    return "\n".join(lines)


def plot_pattern(
    ax, q_exp, a, b, peaks, title,
    h_max, k_max,
    show_labels=True,
    show_lattice_lines=True,
    ring_margin=0.5
):
    theta = np.linspace(0, np.pi / 2, 400)

    # Debye rings
    for q in q_exp:
        x = q * np.cos(theta)
        y = q * np.sin(theta)
        ax.plot(x, y, linewidth=1)

    # lattice grid
    if show_lattice_lines:
        draw_lattice_grid(ax, a, b, h_max, k_max)

    # reciprocal lattice points
    qx_vals = [q_hk_x(h, a) for h, k, q in peaks]
    qy_vals = [q_hk_y(k, b) for h, k, q in peaks]

    ax.scatter(qx_vals, qy_vals, s=15)

    if show_labels:
        for (h, k, q), x, y in zip(peaks, qx_vals, qy_vals):
            ax.text(x + 0.03, y + 0.03, f"({h}{k})", fontsize=8)

    x_max_points = max(qx_vals) if qx_vals else 0
    y_max_points = max(qy_vals) if qy_vals else 0
    q_max_exp = max(q_exp) if len(q_exp) > 0 else 0

    x_max = max(x_max_points, q_max_exp) + ring_margin
    y_max = max(y_max_points, q_max_exp) + ring_margin
    qmax = max(x_max, y_max)

    ax.set_title(title)
    ax.set_xlabel("q_x")
    ax.set_ylabel("q_y")
    ax.set_xlim(0, qmax)
    ax.set_ylim(0, qmax)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)

    # =====================================================
    # 複数選択用
    # =====================================================
    selected_hk = set()
    selected_scatter = [None]

    def get_toolbar():
        manager = getattr(ax.figure.canvas, "manager", None)
        if manager is None:
            return None
        return getattr(manager, "toolbar", None)

    def update_selected_plot():
        if selected_scatter[0] is not None:
            selected_scatter[0].remove()
            selected_scatter[0] = None

        if len(selected_hk) == 0:
            return

        xs = [q_hk_x(h, a) for (h, k) in selected_hk]
        ys = [q_hk_y(k, b) for (h, k) in selected_hk]
        selected_scatter[0] = ax.scatter(xs, ys, s=90, color="red", zorder=5)

    def find_nearest_point(x_click, y_click):
        min_dist = np.inf
        nearest = None

        for h, k, q in peaks:
            x = q_hk_x(h, a)
            y = q_hk_y(k, b)
            dist = (x - x_click) ** 2 + (y - y_click) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = (h, k)

        return nearest, min_dist

    def on_click(event):
        toolbar = get_toolbar()

        # zoom / pan ツールがONの最中だけ選択しない
        # zoomした後、ツールをOFFにした状態では選択できる
        if toolbar is not None and hasattr(toolbar, "mode"):
            if toolbar.mode in ["zoom rect", "pan/zoom"]:
                return

        if event.inaxes != ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        # 現在のzoom範囲を保存
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        # 右クリックで全解除
        if event.button == 3:
            selected_hk.clear()
            update_selected_plot()

            # 選択更新後にzoom範囲を復元
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.figure.canvas.draw_idle()

            print(f"{title}: 選択をクリアしました")
            return

        # 左クリック以外は無視
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
            print(f"{title}: 解除 ({nearest[0]}{nearest[1]})")
        else:
            selected_hk.add(nearest)
            print(f"{title}: 追加 ({nearest[0]}{nearest[1]})")

        update_selected_plot()

        # update後にzoom範囲を復元
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.figure.canvas.draw_idle()

    def on_key(event):
        if event.key is None:
            return

        if event.key.lower() != "c":
            return

        if len(selected_hk) == 0:
            return

        text = build_selected_d_table(selected_hk, a, b)
        pyperclip.copy(text)

        print(f"\n{title}: 選択点をクリップボードにコピーしました")
        print("形式: miller / h / k / l / d / d_over_dmax")
        print(text)
        print()

    fig = ax.figure
    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)

    return selected_hk, update_selected_plot

# =========================================================
# MAIN
# =========================================================

q_exp = input_q_values()

if len(q_exp) < 2:
    raise ValueError("少なくとも2本のq値が必要です。")

q1, q2 = q_exp[0], q_exp[1]

# ---------------------------------------------------------
# Centered rectangular A
# ---------------------------------------------------------
aA, bA = calc_ab_pattern_A(q1, q2)
h_max_A, k_max_A = auto_hk_max_from_qmax(aA, bA, q_exp)
hk_list_A = generate_hk_list(
    h_max=h_max_A,
    k_max=k_max_A,
    centered=True,
    use_centering_rule=use_centering_rule
)
peaksA = theory_peaks(aA, bA, hk_list_A)

# ---------------------------------------------------------
# Centered rectangular B
# ---------------------------------------------------------
aB, bB = calc_ab_pattern_B(q1, q2)
h_max_B, k_max_B = auto_hk_max_from_qmax(aB, bB, q_exp)
hk_list_B = generate_hk_list(
    h_max=h_max_B,
    k_max=k_max_B,
    centered=True,
    use_centering_rule=use_centering_rule
)
peaksB = theory_peaks(aB, bB, hk_list_B)

# ---------------------------------------------------------
# P2m
# ---------------------------------------------------------
aP, bP = calc_ab_pattern_P2m(q1, q2)
h_max_P, k_max_P = auto_hk_max_from_qmax(aP, bP, q_exp)
hk_list_P = generate_hk_list(
    h_max=h_max_P,
    k_max=k_max_P,
    centered=False,
    use_centering_rule=False
)
peaksP = theory_peaks(aP, bP, hk_list_P)

# print
print("\nExperimental q values:")
for i, q in enumerate(q_exp, start=1):
    print(f"{i:>2d}: {q:.4f}")

print(f"\nCentered A: h_max = {h_max_A}, k_max = {k_max_A}")
print(f"Centered B: h_max = {h_max_B}, k_max = {k_max_B}")
print(f"P2m:        h_max = {h_max_P}, k_max = {k_max_P}")

print_theory_table(
    "Centered A: 1st=(110), 2nd=(200)",
    aA, bA, peaksA,
    n_print=n_theory_to_print
)

print_theory_table(
    "Centered B: 1st=(200), 2nd=(110)",
    aB, bB, peaksB,
    n_print=n_theory_to_print
)

print_theory_table(
    "P2m: 1st=(10), 2nd=(01)",
    aP, bP, peaksP,
    n_print=n_theory_to_print
)

assignA = nearest_theory_assignments(q_exp, peaksA)
assignB = nearest_theory_assignments(q_exp, peaksB)
assignP = nearest_theory_assignments(q_exp, peaksP)

print_assignment_table("Centered A", assignA)
print_assignment_table("Centered B", assignB)
print_assignment_table("P2m", assignP)

# plot
fig, axes = plt.subplots(1, 3, figsize=(12, 6))

selA, updateA = plot_pattern(
    axes[0],
    q_exp=q_exp,
    a=aA,
    b=bA,
    peaks=peaksA,
    title=f"C2/m type A\n1st=(110), 2nd=(200)\na={aA:.3f}, b={bA:.3f}",
    h_max=h_max_A,
    k_max=k_max_A,
    show_labels=show_labels,
    show_lattice_lines=show_lattice_lines,
    ring_margin=ring_margin
)

selB, updateB = plot_pattern(
    axes[1],
    q_exp=q_exp,
    a=aB,
    b=bB,
    peaks=peaksB,
    title=f"C2/m type B\n1st=(200), 2nd=(110)\na={aB:.3f}, b={bB:.3f}",
    h_max=h_max_B,
    k_max=k_max_B,
    show_labels=show_labels,
    show_lattice_lines=show_lattice_lines,
    ring_margin=ring_margin
)

selP, updateP = plot_pattern(
    axes[2],
    q_exp=q_exp,
    a=aP,
    b=bP,
    peaks=peaksP,
    title=f"P2m\n1st=(10), 2nd=(01)\na={aP:.3f}, b={bP:.3f}",
    h_max=h_max_P,
    k_max=k_max_P,
    show_labels=show_labels,
    show_lattice_lines=show_lattice_lines,
    ring_margin=ring_margin
)

def auto_select_nearest_for_graph(selected_hk, update_func, assignments, title):
    selected_hk.clear()

    for q, h, k, qcalc, diff, rel in assignments:
        selected_hk.add((h, k))

    update_func()
    fig.canvas.draw_idle()

    print(f"\n{title}: 最近接点を自動選択しました")
    print_assignment_table(title, assignments)
    print("c キーで選択点の d 値をクリップボードにコピーできます")

plt.subplots_adjust(bottom=0.18)

ax_auto_A = plt.axes([0.18, 0.04, 0.16, 0.06])
ax_auto_B = plt.axes([0.42, 0.04, 0.16, 0.06])
ax_auto_P = plt.axes([0.66, 0.04, 0.16, 0.06])

btn_auto_A = Button(ax_auto_A, "Auto A")
btn_auto_B = Button(ax_auto_B, "Auto B")
btn_auto_P = Button(ax_auto_P, "Auto P")

btn_auto_A.on_clicked(
    lambda event: auto_select_nearest_for_graph(
        selA, updateA, assignA, "C2/m type A"
    )
)

btn_auto_B.on_clicked(
    lambda event: auto_select_nearest_for_graph(
        selB, updateB, assignB, "C2/m type B"
    )
)

btn_auto_P.on_clicked(
    lambda event: auto_select_nearest_for_graph(
        selP, updateP, assignP, "P2m"
    )
)

plt.tight_layout(rect=[0, 0.16, 1, 1], pad=0.5)
plt.show()
