import matplotlib

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import subprocess


# === Load data ===
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

    # === Input ONCE (apply to all files) ===
    scale = float(input("Reference scale factor (default=1): ") or 1)
    height = float(input("Min peak height (default=15): ") or 15)
    distance = int(input("Peak distance (default=5): ") or 5)

    ref_data = load_data(os.path.join(ref_dir, ref_file))

    instruction_text = (
        "Click index: Select / Deselect\n"
        "Press C: Copy selected peaks\n"
        "Press Q: Next file\n"
        "Press Z: Zoom to rectangle (toggle)"
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

        diff_intensity = sample_data['Intensity'] - scale * ref_data['Intensity']

        peaks, _ = detect_peaks(diff_intensity, height, distance)

        if len(peaks) == 0:
            print("No peaks detected.")
            continue

        # === Plot ===
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(sample_data['Q'], diff_intensity)
        ax.plot(sample_data['Q'].iloc[peaks],
                diff_intensity.iloc[peaks],
                'ro')

        ax.set_title(sample_file)
        ax.set_xlabel("Q")
        ax.set_ylabel("Sample - scale*Ref")
        ax.grid(True)

        selected = set()
        text_objects = {}

        # === Display GLOBAL index ===
        for idx in peaks:
            q = sample_data['Q'].iloc[idx]
            y = diff_intensity.iloc[idx]

            txt = ax.text(q, y, str(idx),
                          color='blue',
                          fontsize=9,
                          picker=True)

            text_objects[txt] = idx

        # === KEY instruction (OUTSIDE PLOT) ===
        fig.text(
            0.01, 0.98,
            instruction_text,
            fontsize=10,
            verticalalignment='top'
        )

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

            # COPY selected peaks
            if event.key.lower() == "c":

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

                subprocess.run("pbcopy", text=True, input=text_block)

                print("\nCopied:\n")
                print(text_block)

            # NEXT file
            elif event.key.lower() == "q":
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
