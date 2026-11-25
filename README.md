# Wihok (วิหค)

Drop in a song and get a karaoke track (music only), an acapella track (vocals
only), and the song's BPM and key. Everything runs on your own computer; no audio
is uploaded anywhere. You can also listen to the original, karaoke and acapella
tracks in the app and correct the BPM and key by hand.

Status: v1, for personal use on Windows. There is no installer yet.

## What you need

- Windows 10 or 11.
- An NVIDIA GPU is strongly recommended (developed on an RTX 3070 Ti with 8 GB).
  Without one the app falls back to the CPU, which is much slower.
- Python 3.12.
- FFmpeg, only for `.m4a` files. mp3, wav and flac files work without it.

## Set up

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This installs the CUDA build of PyTorch (several GB), so it takes a while.
Check that the GPU is visible:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

It should print `True`. The first separation also downloads the Demucs model once.

## Run

Double-click `Wihok.bat`, or:

```powershell
.\.venv\Scripts\python.exe main.py
```

Drop a song on the window (mp3, wav, flac or m4a). Results are saved in
`Music\Wihok\<song name>-<short id>\` as `<song>_karaoke.wav` and
`<song>_acapella.wav`. Processing the same song again reuses the earlier results
and never overwrites them.

A command-line version is also available: `python cli.py "path\to\song.mp3"`.

## Look

The window has its own title bar (drag it to move, double-click to maximize, drag
an edge to resize) and a light and a dark theme. The sun/moon button in the title
bar switches theme; the first launch follows Windows. The language, the theme and
nothing else are remembered between runs.

The text uses the bundled pixel font TA GBA monothai MAX, which looks sharpest at
100% display scaling. See "Fonts" below.

## Fonts

`assets/fonts/TA GBA monothai_MAX.ttf` is by Taweechai Assawarangsitsang (TA Font),
licensed under the SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). It is used
unmodified. It is an experimental pixel font, so some Thai letters are simplified.

## The separation model and its license

Wihok uses the `htdemucs` model from [Demucs](https://github.com/adefossez/demucs). The Demucs
code is MIT licensed. The trained weights are a different matter: their author states that
"the license of the weights is not clear", because the training data includes MUSDB material
that was only usable for research, and that the weights may fall under a non-commercial
license. Wihok therefore does **not** ship the weights. The first time you separate a song the
app downloads them (about 80 MB) from the author's own page,
[adefossez/HTDemucs](https://huggingface.co/adefossez/HTDemucs), so you need an internet
connection once. Treat the results as for personal, non-commercial use unless you have
cleared the license yourself.

## License

Wihok is released under the MIT License (see `LICENSE`). It uses many open-source libraries,
each under its own license; they are listed with their license texts in
`THIRD-PARTY-NOTICES.txt` (regenerate it with `python packaging/make_notices.py`). The font is
under the SIL Open Font License (`assets/fonts/OFL.txt`). The NVIDIA CUDA libraries inside the GPU
add-on are NVIDIA software and are not covered by the MIT license. The separation model is not
included; see the section above.

## Building the installer

You need Inno Setup 6 and two Python 3.12 environments: `.venv` (`requirements.txt`, CUDA build
of PyTorch) and `.venv-cpu` (`requirements-cpu.txt`). Then:

```powershell
.\packaging\build.ps1 -PackUrl https://github.com/Babyferret/wihok/releases/download/v<version>/Wihok-CUDA-Pack-<version>.exe
.\packaging\test-installer.ps1      # needs a build whose -PackUrl is http://localhost:8099/Wihok-CUDA-Pack-<version>.exe
```

This produces `build\installer\Wihok-Setup-<version>.exe` (about 190 MB, the CPU build) and
`Wihok-CUDA-Pack-<version>.exe` (about 1.7 GB, the GPU add-on that the installer downloads for
NVIDIA users). Upload both to the same GitHub release, tagged `v<version>`; the version number
lives in `core/version.py`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests that use real songs are skipped unless `WIHOK_SAMPLES` points at a folder
with them and `samples/wihok-samples.json` says which songs to use and what to expect
(the format is described in `tests/samples.py`). The songs and that file are not part of
this repository.

## Layout

```
main.py        starts the app
cli.py         command-line version
core/          the work: separation, BPM and key, output folders (no Qt)
ui/            the PySide6 window, title bar, player, worker thread, text and themes
tests/         tests for core
assets/        app icon and the bundled font
```

---

## วิหค (ภาษาไทย)

ลากเพลงมาวาง ได้แทร็กคาราโอเกะ (เฉพาะดนตรี) แทร็กอะคาเพลลา (เฉพาะเสียงร้อง)
พร้อม BPM และ Key ทำงานในเครื่องของคุณทั้งหมด ไม่ส่งไฟล์ขึ้นอินเทอร์เน็ต
ฟังแทร็กต้นฉบับ คาราโอเกะ และอะคาเพลลาในแอปได้ และแก้ BPM กับ Key เองได้

ตอนนี้เป็นเวอร์ชัน v1 สำหรับใช้เองบน Windows ยังไม่มีตัวติดตั้ง

**ติดตั้ง:** ต้องมี Python 3.12 แล้วรันสองคำสั่งในหัวข้อ "Set up" ด้านบน
(การ์ดจอ NVIDIA ช่วยให้เร็วขึ้นมาก ถ้าไม่มีจะใช้ CPU ซึ่งช้ากว่า)
ไฟล์ `.m4a` ต้องมี FFmpeg เพิ่ม ส่วน mp3, wav และ flac ไม่ต้อง

**เปิดแอป:** ดับเบิลคลิก `Wihok.bat` ผลลัพธ์อยู่ที่ `Music\Wihok\`
เพลงที่เคยทำแล้วจะใช้ผลเดิม ไม่ทับไฟล์เก่า และเลือกภาษาไทยได้จากมุมขวาบนของแอป

**โมเดลแยกเสียง:** ผู้สร้าง Demucs ระบุเองว่าใบอนุญาตของน้ำหนักโมเดล "ไม่ชัดเจน" (ข้อมูลฝึกมี
MUSDB ที่เดิมใช้ได้เฉพาะงานวิจัย และอาจเข้าข่ายไม่อนุญาตให้ใช้เชิงพาณิชย์) วิหคจึงไม่แจกจ่ายตัวโมเดล
ครั้งแรกที่แยกเสียงแอปจะดาวน์โหลดจากหน้าของผู้สร้างเอง (ประมาณ 80 MB ต้องมีอินเทอร์เน็ตหนึ่งครั้ง)
ควรใช้ผลลัพธ์เพื่อส่วนตัวและไม่ใช่เชิงพาณิชย์ เว้นแต่คุณตรวจสอบสิทธิ์เอง
