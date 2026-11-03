"""Prüft den Gesichts-Zuschnitt (facecrop.py) im fertigen Image.

Baut ein Querformat-Video, in dem ein Foto (NASA, gemeinfrei) nach vier Sekunden von links nach rechts wandert,
und erwartet: Gesicht fast immer gefunden, der Ausschnitt folgt von links nach rechts.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import facecrop  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        mp4 = os.path.join(tmp, "face.mp4")
        # Foto 420 px breit, bewegt sich ab Sekunde 4 in vier Sekunden von x=100 nach x=1300
        x = "if(lt(t,4),100,if(lt(t,8),100+1200*(t-4)/4,1300))"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x284060:s=1920x1080:r=10:d=12",
                        "-loop", "1", "-i", os.path.join(HERE, "fixtures", "face.jpg"), "-filter_complex",
                        f"[1:v]scale=420:-2[f];[0:v][f]overlay=x='{x}':y=300:shortest=1", "-t", "12", "-pix_fmt", "yuv420p", mp4],
                       check=True)
        samples = facecrop.detect(mp4, 0, 12, 1920, 1080)
        assert samples, "keine Messungen (OpenCV fehlt?)"
        found = sum(v is not None for _, v in samples) / len(samples)
        assert found > 0.9, f"Gesicht nur in {found:.0%} der Messungen gefunden"
        pts = facecrop.smooth(samples)
        assert pts and pts[0][1] < 0.3 and pts[-1][1] > 0.7, f"Ausschnitt folgt nicht: {pts}"
        plan = facecrop.plan(mp4, 0, 12, 1920, 1080, 1080, 1920)
        assert plan and plan[1] == 3413 and "lt(t" in plan[2]
        # ohne Gesicht: kein Zuschnitt
        blank = os.path.join(tmp, "blank.mp4")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=1920x1080:r=10:d=4",
                        "-pix_fmt", "yuv420p", blank], check=True)
        assert facecrop.plan(blank, 0, 4, 1920, 1080, 1080, 1920) is None
    print("facecrop ok", f"{found:.0%}", [(round(t, 1), round(float(v), 2)) for t, v in pts])


if __name__ == "__main__":
    main()
