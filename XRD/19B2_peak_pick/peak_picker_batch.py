import matplotlib

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import subprocess
import pyperclip
from matplotlib.widgets import Button, TextBox


# === Load data ===
# .dat版の読み込み条件は維持：skiprows=24, tab区切り, Q/Intensity/Error の3列

def load_data(filepath, skip_rows=24):
    data = pd.read_csv(filepath, skiprows=skip_rows, sep="\t", header=None)
    data.columns = ['Q', 'Intensity', 'Error']
    return data


# === Peak detection ===
def detect_peaks(intensity, height, distance):
    peaks, properties = find_peaks(intensity, height=height, distance=distance)
    return peaks, properties


def main():

    script_dir = os.getcwd()

    # === Sort sample files ascending ===
    dat_files = sorted([f for f in os.listdir(script_dir) if f.endswith(".dat")])

    if not dat_files:
        print("No sample .dat files found.")
        return

    print("Detected sample files (ascending order):")
    for f in dat_files:
        print(f)

    # === Reference (single file only) ===
    ref_dir = os.path.join(script_dir, "ref")
    ref_files = [f for f in os.listdir(ref_dir) if f.endswith(".dat")]

    if len(ref_files) != 1:
        print("Put exactly one .dat file in ref folder.")
        return

    ref_file = ref_files[0]
    print(f"\nReference: {ref_file}")

    # === Settings inherited by next file ===
    # Applyを押した時点の値が、この辞書に保存される。
    # 次のファイルでは、この値がTextBoxの初期値になる。
    settings = {
        "scale": 1.0,
        "height": 15.0,
        "distance": 5,
    }

    ref_data = load_data(os.path.join(ref_dir, ref_file))

    instruction_text = (
        "Click index: Select / Deselect\n"
        "Press C: Copy selected peaks\n"
        "Press Q: Next file\n"
        "Press Z: Zoom to rectangle (toggle)\n"
        "Edit Scale / Height / Distance, then Apply: Re-detect peaks"
    )

    print("\n=== Instructions ===")
    print(instruction_text)

    # === Loop over all sample files ===
    for sample_file in dat_files:

        print(f"\nProcessing: {sample_file}")

        sample_data = load_data(os.path.join(script_dir, sample_file))

        if len(sample_data) != len(ref_data):
            print("Length mismatch. Skipping.")
            continue

        # === State for current file ===
        state = {
            "scale": settings["scale"],
            "height": settings["height"],
            "distance": settings["distance"],
            "diff_intensity": None,
            "peaks": np.array([], dtype=int),
        }

        selected = set()
        text_objects = {}
        plotted_artists = []

        # === Plot ===
        fig, ax = plt.subplots(figsize=(11, 7))
        plt.subplots_adjust(bottom=0.22, top=0.82)

        fig.text(
            0.01, 0.98,
            instruction_text,
            fontsize=10,
            verticalalignment='top'
        )

        # TextBox / Button area

        ax_scale_label = plt.axes([0.05, 0.12, 0.22, 0.03])
        ax_scale_label.axis("off")
        ax_scale_label.text(0.0, 0.5, "Reference scale factor", fontsize=10, va="center")

        ax_scale = plt.axes([0.05, 0.07, 0.22, 0.045])
        scale_box = TextBox(ax_scale, "", initial=str(state["scale"]))

        ax_height_label = plt.axes([0.33, 0.12, 0.22, 0.03])
        ax_height_label.axis("off")
        ax_height_label.text(0.0, 0.5, "Min peak height", fontsize=10, va="center")

        ax_height = plt.axes([0.33, 0.07, 0.22, 0.045])
        height_box = TextBox(ax_height, "", initial=str(state["height"]))

        ax_distance_label = plt.axes([0.61, 0.12, 0.22, 0.03])
        ax_distance_label.axis("off")
        ax_distance_label.text(0.0, 0.5, "Peak distance", fontsize=10, va="center")

        ax_distance = plt.axes([0.61, 0.07, 0.22, 0.045])
        distance_box = TextBox(ax_distance, "", initial=str(state["distance"]))

        ax_apply = plt.axes([0.86, 0.07, 0.10, 0.045])
        apply_button = Button(ax_apply, "Apply")

        def calculate_current_diff_and_peaks():
            state["diff_intensity"] = sample_data['Intensity'] - state["scale"] * ref_data['Intensity']
            state["peaks"], _ = detect_peaks(
                state["diff_intensity"],
                state["height"],
                state["distance"]
            )

        def draw_plot():
            ax.clear()
            selected.clear()
            text_objects.clear()
            plotted_artists.clear()

            diff_intensity = state["diff_intensity"]
            peaks = state["peaks"]

            ax.plot(sample_data['Q'], diff_intensity)

            if len(peaks) > 0:
                ax.plot(sample_data['Q'].iloc[peaks],
                        diff_intensity.iloc[peaks],
                        'ro')

                # === Display GLOBAL index ===
                for idx in peaks:
                    q = sample_data['Q'].iloc[idx]
                    y = diff_intensity.iloc[idx]

                    txt = ax.text(q, y, str(idx),
                                  color='blue',
                                  fontsize=9,
                                  picker=True)
                    text_objects[txt] = idx
            else:
                ax.text(
                    0.5, 0.95,
                    "No peaks detected. Change Height / Distance and Apply.",
                    transform=ax.transAxes,
                    ha="center",
                    va="top",
                    fontsize=10
                )

            ax.set_title(
                f"{sample_file}    scale={state['scale']}  height={state['height']}  distance={state['distance']}"
            )
            ax.set_xlabel("Q")
            ax.set_ylabel("Sample - scale*Ref")
            ax.grid(True)
            fig.canvas.draw_idle()

        def apply_settings(event=None):
            try:
                new_scale = float(scale_box.text)
                new_height = float(height_box.text)
                new_distance = int(float(distance_box.text))

                if new_distance < 1:
                    raise ValueError("Distance must be >= 1")

            except Exception as e:
                print(f"Invalid setting: {e}")
                return

            state["scale"] = new_scale
            state["height"] = new_height
            state["distance"] = new_distance

            # 次ファイルへ引き継ぐ
            settings["scale"] = new_scale
            settings["height"] = new_height
            settings["distance"] = new_distance

            calculate_current_diff_and_peaks()
            draw_plot()

            print(
                f"Applied: scale={new_scale}, height={new_height}, "
                f"distance={new_distance}, peaks={len(state['peaks'])}"
            )

        # Initial detection with inherited settings
        calculate_current_diff_and_peaks()
        draw_plot()

        apply_button.on_clicked(apply_settings)

        # Press Enter in any TextBox to apply/re-detect
        scale_box.on_submit(apply_settings)
        height_box.on_submit(apply_settings)
        distance_box.on_submit(apply_settings)

        # === Mouse click ===
        def on_pick(event):
            txt = event.artist
            if txt not in text_objects:
                return

            idx = text_objects[txt]

            if idx in selected:
                selected.remove(idx)
                txt.set_color('blue')
            else:
                selected.add(idx)
                txt.set_color('red')

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("pick_event", on_pick)

        # === Keyboard ===
        def on_key(event):

            if event.key is None:
                return

            # COPY selected peaks
            if event.key.lower() == "c":

                if not selected:
                    print("No peaks selected.")
                    return

                selected_sorted = sorted(selected)
                diff_intensity = state["diff_intensity"]
                scale_now = state["scale"]

                output_lines = []

                for idx in selected_sorted:

                    col0 = idx
                    col1 = sample_data['Q'].iloc[idx]
                    col2 = scale_now * ref_data['Intensity'].iloc[idx]
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
            elif event.key.lower() == "q":
                # qで進んだ場合も、現在TextBoxに入っている値を次へ引き継ぐ
                apply_settings()
                plt.close(fig)

            # ZOOM TO RECTANGLE (toggle)
            elif event.key.lower() == "z":
                toolbar = fig.canvas.manager.toolbar
                if toolbar is not None:
                    toolbar.zoom()
                else:
                    print("Toolbar not available.")

        fig.canvas.mpl_connect("key_press_event", on_key)

        plt.show()

    print("\nAll files processed.")


if __name__ == "__main__":
    main()
