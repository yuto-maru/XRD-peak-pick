# excel_range_to_word_table_gui.py

import tkinter as tk
from tkinter.scrolledtext import ScrolledText


OUTPUT_HEADERS = ["q (nm–1)", "d-spacing (nm)", "ratio", "ratio (calc.)", "hkl"]

USE_COLOR = "#d8f5d0"      # 緑：使用
REMOVE_COLOR = "#ffd6d6"   # 赤：除外
HEADER_COLOR = "#dddddd"
INFO_COLOR = "#eef2ff"


data = []
original_headers = []
column_roles = []
cell_selected = []
col_selected = []
row_selected = []
hidden_cols = set()


# =====================
# 文字列処理
# =====================

def parse_excel_text(raw):
    raw = raw.strip("\n")

    if raw.strip() == "":
        return []

    lines = raw.split("\n")
    parsed = []

    for line in lines:
        cells = line.split("\t")

        row = []
        for cell in cells:
            value = cell.strip()
            if value == "":
                value = "–"
            row.append(value)

        parsed.append(row)

    max_cols = max(len(row) for row in parsed)

    for row in parsed:
        while len(row) < max_cols:
            row.append("–")

    return parsed


def make_default_headers(n_cols):
    return [f"列{i + 1}" for i in range(n_cols)]


def get_single_col_number(entry, max_col):
    text = entry.get().strip()

    if text == "":
        return None

    try:
        n = int(text)
    except ValueError:
        return None

    if 1 <= n <= max_col:
        return n - 1

    return None


def all_column_entries_empty():
    entries = [
        q_col_entry,
        d_col_entry,
        ratio_col_entry,
        ratio_calc_col_entry,
        hkl_col_entry,
    ]

    return all(entry.get().strip() == "" for entry in entries)


# =====================
# データ読み込み・列設定
# =====================

def load_range():
    global data, original_headers, column_roles
    global cell_selected, col_selected, row_selected, hidden_cols

    raw = input_text.get("1.0", tk.END)
    parsed = parse_excel_text(raw)

    if not parsed:
        status_label.config(text="データがありません")
        return

    if use_first_row_as_header_var.get():
        original_headers = parsed[0]
        data = parsed[1:]
    else:
        data = parsed
        original_headers = make_default_headers(len(data[0]))

    if not data:
        status_label.config(text="ヘッダー以外のデータがありません")
        return

    n_rows = len(data)
    n_cols = len(data[0])

    column_roles = ["使わない" for _ in range(n_cols)]
    col_selected = [True for _ in range(n_cols)]
    row_selected = [True for _ in range(n_rows)]
    cell_selected = [[True for _ in range(n_cols)] for _ in range(n_rows)]
    hidden_cols = set()

    apply_column_settings(redraw=False)

    draw_table()
    status_label.config(text=f"{n_rows} 行 × {n_cols} 列を読み込みました")


def apply_column_settings(redraw=True):
    """
    列番号指定がすべて空欄の場合：
        全列を表示・使用する。
    1つでも列番号指定がある場合：
        指定された列だけを表示・使用する。
    """
    global column_roles, col_selected, hidden_cols

    if not data:
        status_label.config(text="まだデータが読み込まれていません")
        return

    n_cols = len(data[0])

    column_roles = ["使わない" for _ in range(n_cols)]

    # 全部空欄なら、全列をそのまま表示
    if all_column_entries_empty():
        hidden_cols = set()
        col_selected = [True for _ in range(n_cols)]

        for c in range(n_cols):
            if c < len(OUTPUT_HEADERS):
                column_roles[c] = OUTPUT_HEADERS[c]
            else:
                column_roles[c] = f"列{c + 1}"

        if redraw:
            draw_table()
            status_label.config(text="列番号指定が空欄のため、全列を表示しました")

        return

    role_entries = [
        ("q (nm–1)", q_col_entry),
        ("d-spacing (nm)", d_col_entry),
        ("ratio", ratio_col_entry),
        ("ratio (calc.)", ratio_calc_col_entry),
        ("hkl", hkl_col_entry),
    ]

    used_cols = set()

    for role, entry in role_entries:
        c = get_single_col_number(entry, n_cols)

        if c is not None:
            column_roles[c] = role
            used_cols.add(c)

    # 指定されていない列を非表示にする
    hidden_cols = set(range(n_cols)) - used_cols

    # 指定された列だけ使用状態にする
    col_selected = [False for _ in range(n_cols)]

    for c in used_cols:
        col_selected[c] = True

    if redraw:
        draw_table()
        status_label.config(text="列番号指定を反映しました")


# =====================
# 表示用
# =====================

def format_value(value, role):
    if role == "hkl":
        v = value.replace(" ", "")

        # 2桁なら頭に0追加
        if len(v) == 2:
            v = "0" + v

        return v

    return value


def make_clickable_label(parent, text, bg, command, width=16, anchor="w"):
    label = tk.Label(
        parent,
        text=text,
        width=width,
        relief="solid",
        borderwidth=1,
        bg=bg,
        anchor=anchor,
        padx=4,
        pady=3
    )

    label.bind("<Button-1>", lambda event: command())
    label.bind("<Enter>", lambda event: label.config(cursor="hand2"))

    return label


def draw_table():
    for widget in table_frame.winfo_children():
        widget.destroy()

    if not data:
        return

    n_rows = len(data)
    n_cols = len(data[0])

    visible_cols = [c for c in range(n_cols) if c not in hidden_cols]

    # 左上
    tk.Label(
        table_frame,
        text="",
        width=6,
        relief="solid",
        borderwidth=1,
        bg=HEADER_COLOR
    ).grid(row=0, column=0, sticky="nsew")

    tk.Label(
        table_frame,
        text="指定",
        width=6,
        relief="solid",
        borderwidth=1,
        bg=INFO_COLOR
    ).grid(row=1, column=0, sticky="nsew")

    # 列ヘッダー
    display_col = 1

    for c in visible_cols:
        active = col_selected[c] and column_roles[c] != "使わない"
        bg = USE_COLOR if active else REMOVE_COLOR

        label = make_clickable_label(
            table_frame,
            text=f"{c + 1}: {original_headers[c]}",
            bg=bg,
            command=lambda x=c: toggle_col(x),
            width=18,
            anchor="center"
        )
        label.grid(row=0, column=display_col, sticky="nsew")

        role_text = column_roles[c]

        if not col_selected[c]:
            role_text = "除外"

        tk.Label(
            table_frame,
            text=role_text,
            width=18,
            relief="solid",
            borderwidth=1,
            bg=INFO_COLOR if col_selected[c] else REMOVE_COLOR,
            anchor="center"
        ).grid(row=1, column=display_col, sticky="nsew")

        display_col += 1

    # 行番号・セル
    for r in range(n_rows):
        row_bg = USE_COLOR if row_selected[r] else REMOVE_COLOR

        row_label = make_clickable_label(
            table_frame,
            text=f"{r + 1}",
            bg=row_bg,
            command=lambda x=r: toggle_row(x),
            width=6,
            anchor="center"
        )
        row_label.grid(row=r + 2, column=0, sticky="nsew")

        display_col = 1

        for c in visible_cols:
            selected = (
                row_selected[r]
                and col_selected[c]
                and column_roles[c] != "使わない"
                and cell_selected[r][c]
            )

            bg = USE_COLOR if selected else REMOVE_COLOR

            cell_label = make_clickable_label(
                table_frame,
                text=data[r][c],
                bg=bg,
                command=lambda rr=r, cc=c: toggle_cell(rr, cc),
                width=18,
                anchor="w"
            )
            cell_label.grid(row=r + 2, column=display_col, sticky="nsew")

            display_col += 1


# =====================
# トグル操作
# =====================

def toggle_cell(r, c):
    cell_selected[r][c] = not cell_selected[r][c]
    draw_table()


def toggle_col(c):
    if c in hidden_cols:
        return

    col_selected[c] = not col_selected[c]
    draw_table()


def toggle_row(r):
    row_selected[r] = not row_selected[r]
    draw_table()


def clear_all():
    """
    クリアしても列番号指定欄は残す。
    """
    global data, original_headers, column_roles
    global cell_selected, col_selected, row_selected, hidden_cols

    data = []
    original_headers = []
    column_roles = []
    cell_selected = []
    col_selected = []
    row_selected = []
    hidden_cols = set()

    input_text.delete("1.0", tk.END)
    output_text.delete("1.0", tk.END)

    for widget in table_frame.winfo_children():
        widget.destroy()

    status_label.config(text="クリアしました。列番号指定は保持されています。")


# =====================
# 出力
# =====================

def generate_output():
    if not data:
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "まだデータが読み込まれていません")
        return

    # 生成前に列番号指定を反映
    apply_column_settings(redraw=True)

    n_rows = len(data)
    n_cols = len(data[0])

    output_columns = []

    # 列番号指定が空欄なら表示中の全列をそのまま出力
    if all_column_entries_empty():
        for c in range(n_cols):
            if c not in hidden_cols and col_selected[c]:
                output_columns.append((c, column_roles[c]))

    else:
        # 出力順を固定
        for role in OUTPUT_HEADERS:
            for c in range(n_cols):
                if (
                    c not in hidden_cols
                    and col_selected[c]
                    and column_roles[c] == role
                ):
                    output_columns.append((c, role))

    if not output_columns:
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "使用する列がありません")
        return

    # 列ごとに、使用するセルだけを集める
    # 不要セルはその列だけ削除され、下のセルが繰り上がる
    column_values = []

    for c, role in output_columns:
        values = []

        for r in range(n_rows):
            # 行ごと除外されている場合は全列で無視
            if not row_selected[r]:
                continue

            # セルが使用状態なら追加、不要セルなら追加しない
            if cell_selected[r][c]:
                value = format_value(data[r][c], role)
                values.append(value)

        column_values.append(values)

    max_len = max(len(values) for values in column_values)

    output_lines = []

    output_headers = [role for c, role in output_columns]
    output_lines.append("\t".join(output_headers))

    for i in range(max_len):
        row_values = []

        for values in column_values:
            if i < len(values):
                row_values.append(values[i])
            else:
                row_values.append("–")

        output_lines.append("\t".join(row_values))

    output = "\n".join(output_lines)

    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, output)

    status_label.config(text="Word貼り付け用表を生成しました")


def copy_output():
    output = output_text.get("1.0", tk.END).strip("\n")

    if output == "":
        status_label.config(text="コピーする出力がありません")
        return

    root.clipboard_clear()
    root.clipboard_append(output)
    status_label.config(text="出力をクリップボードにコピーしました")


def on_table_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))


# =====================
# GUI
# =====================

root = tk.Tk()
root.title("Excel範囲 → Word Table")
root.geometry("1250x900")


# =====================
# 入力欄
# =====================

tk.Label(
    root,
    text="Excelの範囲をコピーして貼り付け"
).pack(pady=(10, 0))

input_text = ScrolledText(root, width=130, height=7)
input_text.pack(padx=10, pady=5)


# =====================
# 列番号指定
# =====================

column_setting_frame = tk.LabelFrame(root, text="列番号指定")
column_setting_frame.pack(fill=tk.X, padx=10, pady=5)

use_first_row_as_header_var = tk.BooleanVar(value=False)

tk.Checkbutton(
    column_setting_frame,
    text="1行目をヘッダーとして使う",
    variable=use_first_row_as_header_var
).grid(row=0, column=0, padx=5, pady=5, sticky="w")

tk.Label(column_setting_frame, text="q列").grid(row=0, column=1, padx=3)
q_col_entry = tk.Entry(column_setting_frame, width=5)
q_col_entry.grid(row=0, column=2, padx=3)

tk.Label(column_setting_frame, text="d-spacing列").grid(row=0, column=3, padx=3)
d_col_entry = tk.Entry(column_setting_frame, width=5)
d_col_entry.grid(row=0, column=4, padx=3)

tk.Label(column_setting_frame, text="ratio列").grid(row=0, column=5, padx=3)
ratio_col_entry = tk.Entry(column_setting_frame, width=5)
ratio_col_entry.grid(row=0, column=6, padx=3)

tk.Label(column_setting_frame, text="ratio(calc.)列").grid(row=0, column=7, padx=3)
ratio_calc_col_entry = tk.Entry(column_setting_frame, width=5)
ratio_calc_col_entry.grid(row=0, column=8, padx=3)

tk.Label(column_setting_frame, text="hkl列").grid(row=0, column=9, padx=3)
hkl_col_entry = tk.Entry(column_setting_frame, width=5)
hkl_col_entry.grid(row=0, column=10, padx=3)


# =====================
# 操作ボタン
# =====================

control_frame = tk.Frame(root)
control_frame.pack(pady=5)

tk.Button(
    control_frame,
    text="読み込み",
    command=load_range,
    bg="lightblue"
).pack(side=tk.LEFT, padx=5)

tk.Button(
    control_frame,
    text="列番号指定を反映",
    command=apply_column_settings
).pack(side=tk.LEFT, padx=5)

tk.Button(
    control_frame,
    text="クリア",
    command=clear_all,
    bg="#ffdddd"
).pack(side=tk.LEFT, padx=5)

tk.Button(
    control_frame,
    text="Word貼り付け用表を生成",
    command=generate_output,
    bg="#cce5ff"
).pack(side=tk.LEFT, padx=5)

tk.Button(
    control_frame,
    text="出力をコピー",
    command=copy_output
).pack(side=tk.LEFT, padx=5)


status_label = tk.Label(root, text="Excel範囲を貼り付けてください")
status_label.pack(pady=5)


# =====================
# 選択テーブル
# =====================

tk.Label(
    root,
    text="列番号指定が空欄なら全列表示。一部でも指定すると指定列だけ表示。列・行・セルをクリックで使用/除外を切り替え（緑＝使用、赤＝除外）"
).pack()

table_outer_frame = tk.Frame(root)
table_outer_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

canvas = tk.Canvas(table_outer_frame)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

y_scrollbar = tk.Scrollbar(
    table_outer_frame,
    orient=tk.VERTICAL,
    command=canvas.yview
)
y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

x_scrollbar = tk.Scrollbar(
    root,
    orient=tk.HORIZONTAL,
    command=canvas.xview
)
x_scrollbar.pack(fill=tk.X, padx=10)

canvas.configure(
    yscrollcommand=y_scrollbar.set,
    xscrollcommand=x_scrollbar.set
)

table_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=table_frame, anchor="nw")

table_frame.bind("<Configure>", on_table_configure)


# =====================
# 出力欄
# =====================

tk.Label(root, text="Word貼り付け用").pack(pady=(10, 0))

output_text = ScrolledText(root, width=130, height=14)
output_text.pack(padx=10, pady=(5, 10))


root.mainloop()
