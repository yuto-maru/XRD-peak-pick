import matplotlib

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button
from scipy.signal import find_peaks
import pyperclip


# === Load data (.chi) ===
def load_data(filepath, skip_rows=4):
    """
    .chi (空白 or タブ区切り) を読み込み
    NaN行は dropna
    """
    data = pd.read_csv(filepath, skiprows=skip_rows, sep=r"\s+", header=None)
    data.columns = ['Q', 'Intensity', 'Error']
    return data.dropna()


# === Peak detection ===
def detect_peaks(intensity, height, distance):
    peaks, properties = find_peaks(intensity, height=height, distance=distance)
    return peaks, properties


def main():

    script_dir = os.getcwd()

    # === Use .chi only ===
    chi_files = sorted([f for f in os.listdir(script_dir) if f.endswith(".chi")])

    if not chi_files:
        print("No .chi files found.")
        return

    print("Detected .chi files (ascending):")
    for f in chi_files:
        print(f)

    # === Reference (.chi, single) ===
    ref_dir = os.path.join(script_dir, "ref")
    ref_files = [f for f in os.listdir(ref_dir) if f.endswith(".chi")]

    if len(ref_files) != 1:
        print("Put exactly one .chi file in ref folder.")
        return

    ref_file = ref_files[0]
    print(f"\nReference: {ref_file}")

    # === Initial values / inherited values ===
    # Applyで変更した値は current_params に保存され、次の .chi ファイルにも引き継がれる
    current_params = {
        "scale": 1.0,
        "height": 450.0,
        "distance": 5,
    }

    ref_data = load_data(os.path.join(ref_dir, ref_file))

    instruction_text = (
        "Click index: Select / Deselect\n"
        "Press C: Copy selected peaks\n"
        "Press Q: Next file\n"
        "Press Z: Zoom to rectangle (toggle)\n"
        "Edit boxes + Apply: Re-detect peaks"
    )

    print("\n=== Instructions ===")
    print(instruction_text)

    # === Process each sample (.chi) ===
    for sample_file in chi_files:

        print(f"\nProcessing: {sample_file}")

        sample_data = load_data(os.path.join(script_dir, sample_file))

        if len(sample_data) != len(ref_data):
            print("Length mismatch. Skipping.")
            continue

        # Current parameters for this window
        # 前のファイルでApplyした値を初期値として使う
        params = current_params.copy()

        # Objects that change after recalculation
        state = {
            "diff_intensity": None,
            "peaks": np.array([], dtype=int),
            "selected": set(),
            "text_objects": {},
            "line_diff": None,
            "peak_plot": None,
        }

        # === Plot ===
        fig, ax = plt.subplots(figsize=(11, 7))
        plt.subplots_adjust(left=0.08, right=0.98, top=0.82, bottom=0.22)

        ax.set_title(sample_file)
        ax.set_xlabel("Q")
        ax.set_ylabel("Sample - scale*Ref")
        ax.grid(True)

        # === instruction text (outside plot) ===
        fig.text(
            0.01, 0.98,
            instruction_text,
            fontsize=10,
            verticalalignment='top'
        )

        # === TextBox / Button area ===
        ax_scale = plt.axes([0.08, 0.11, 0.18, 0.045])
        ax_height = plt.axes([0.34, 0.11, 0.18, 0.045])
        ax_distance = plt.axes([0.60, 0.11, 0.18, 0.045])
        ax_apply = plt.axes([0.82, 0.11, 0.12, 0.045])

        box_scale = TextBox(ax_scale, "Ref scale ", initial=str(params["scale"]))
        box_height = TextBox(ax_height, "Min height ", initial=str(params["height"]))
        box_distance = TextBox(ax_distance, "Distance ", initial=str(params["distance"]))
        btn_apply = Button(ax_apply, "Apply")

        def recalculate_and_redraw(reset_view=False):
            """Recalculate diff and peaks, then redraw peak markers/text."""
            scale = params["scale"]
            height = params["height"]
            distance = params["distance"]

            diff_intensity = sample_data['Intensity'] - scale * ref_data['Intensity']
            peaks, _ = detect_peaks(diff_intensity, height, distance)

            state["diff_intensity"] = diff_intensity
            state["peaks"] = peaks
            state["selected"] = set()
            state["text_objects"] = {}

            # Main line
            if state["line_diff"] is None:
                (line_diff,) = ax.plot(sample_data['Q'], diff_intensity)
                state["line_diff"] = line_diff
            else:
                state["line_diff"].set_ydata(diff_intensity)

            # Peak markers
            if state["peak_plot"] is not None:
                state["peak_plot"].remove()
                state["peak_plot"] = None

            # Old labels
            for txt in list(ax.texts):
                txt.remove()

            if len(peaks) > 0:
                (peak_plot,) = ax.plot(
                    sample_data['Q'].iloc[peaks],
                    diff_intensity.iloc[peaks],
                    'ro'
                )
                state["peak_plot"] = peak_plot

                # Display index near peaks
                for idx in peaks:
                    q = sample_data['Q'].iloc[idx]
                    y = diff_intensity.iloc[idx]

                    txt = ax.text(
                        q, y, str(idx),
                        color='blue',
                        fontsize=9,
                        picker=True
                    )
                    state["text_objects"][txt] = idx
            else:
                print("No peaks detected with current settings.")

            ax.set_ylabel(f"Sample - {scale}*Ref")
            ax.set_title(
                f"{sample_file}   scale={scale}, height={height}, distance={distance}, peaks={len(peaks)}"
            )

            if reset_view:
                ax.relim()
                ax.autoscale_view()

            fig.canvas.draw_idle()

        def apply_settings(event=None):
            try:
                new_scale = float(box_scale.text.strip() or params["scale"])
                new_height = float(box_height.text.strip() or params["height"])
                new_distance = int(float(box_distance.text.strip() or params["distance"]))

                if new_distance < 1:
                    print("Peak distance must be >= 1.")
                    return

                params["scale"] = new_scale
                params["height"] = new_height
                params["distance"] = new_distance

                # 次のファイルにもこの値を引き継ぐ
                current_params["scale"] = new_scale
                current_params["height"] = new_height
                current_params["distance"] = new_distance

                print(
                    f"Updated: scale={new_scale}, "
                    f"height={new_height}, distance={new_distance}"
                )

                recalculate_and_redraw(reset_view=True)

            except ValueError:
                print("Invalid input. Use numbers: scale=float, height=float, distance=integer.")

        btn_apply.on_clicked(apply_settings)

        # Enter in a TextBox also applies settings
        box_scale.on_submit(apply_settings)
        box_height.on_submit(apply_settings)
        box_distance.on_submit(apply_settings)

        # === Mouse click (select / deselect) ===
        def on_pick(event):
            txt = event.artist
            if txt not in state["text_objects"]:
                return

            idx = state["text_objects"][txt]
            selected = state["selected"]

            if idx in selected:
                selected.remove(idx)
                txt.set_color('blue')
            else:
                selected.add(idx)
                txt.set_color('red')

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("pick_event", on_pick)

        # === Keyboard actions ===
        def on_key(event):

            # COPY selected peaks
            if event.key and event.key.lower() == "c":

                selected = state["selected"]
                diff_intensity = state["diff_intensity"]
                scale = params["scale"]

                if not selected:
                    print("No peaks selected.")
                    return

                selected_sorted = sorted(selected)
                output_lines = []

                for idx in selected_sorted:

                    col0 = idx
                    col1 = sample_data['Q'].iloc[idx]
                    col2 = scale * ref_data['Intensity'].iloc[idx]
                    col3 = sample_data['Intensity'].iloc[idx]
                    col4 = diff_intensity.iloc[idx]
                    col5 = col4
                    col6 = 2 * np.pi / col1

                    line = (f"{col0}\t{col1:.6f}\t{col2:.6f}\t"
                            f"{col3:.6f}\t{col4:.6f}\t"
                            f"{col5:.6f}\t{col6:.6f}")

                    output_lines.append(line)

                text_block = "\n".join(output_lines)

                pyperclip.copy(text_block)

                print("\nCopied:\n")
                print(text_block)

            # NEXT file
            elif event.key and event.key.lower() == "q":
                # Qで次のファイルへ進む前に、入力欄の値を次回用に保存する
                try:
                    current_params["scale"] = float(box_scale.text.strip() or params["scale"])
                    current_params["height"] = float(box_height.text.strip() or params["height"])
                    current_params["distance"] = int(float(box_distance.text.strip() or params["distance"]))
                except ValueError:
                    print("Invalid input. Keeping previous settings for next file.")
                plt.close(fig)

            # ZOOM TO RECTANGLE
            elif event.key and event.key.lower() == "z":
                toolbar = fig.canvas.manager.toolbar
                if toolbar is not None:
                    toolbar.zoom()
                else:
                    print("Toolbar not available.")

        fig.canvas.mpl_connect("key_press_event", on_key)

        # Initial draw
        recalculate_and_redraw(reset_view=True)

        plt.show()

    print("\nAll files processed.")


if __name__ == "__main__":
    main()
