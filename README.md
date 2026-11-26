<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.png">
    <img src="assets/banner-light.png" alt="Wihok (วิหค)" width="640">
  </picture>
</p>

Drop in a song and get a karaoke track (music only), an acapella track (vocals only), and the
song's BPM and key. It all runs on your own computer: your audio is never uploaded. You can listen
to the original, karaoke and acapella tracks inside the app.

[Download](#download) · [Using Wihok](#using-wihok) · [Updates and privacy](#updates-and-privacy) · [ภาษาไทย](#วิหค-ภาษาไทย)

## Download

1. Open the [latest release](https://github.com/Babyferret/wihok/releases/latest).
2. Download `Wihok-Setup-<version>.exe` (about 190 MB) and run it. That is the only file you need.
   If you have an NVIDIA card, the installer offers GPU support and downloads it for you.
3. Windows may show **"Windows protected your PC"** and name an unknown publisher, because the
   installer is not code-signed yet. Choose **More info**, then **Run anyway**.

It installs for your user account only, so it does not ask for an administrator password.

**What you need**

- Windows 10 or 11, 64-bit. Wihok is developed and tested on Windows 10.
- About 0.8 GB of disk space, or about 4 GB with GPU support.
- An internet connection: once for the separation model (about 80 MB, see below), and for update
  checks.
- FFmpeg, only for `.m4a` files. mp3, wav and flac work without it.

## Using Wihok

Drop a song on the window (mp3, wav, flac or m4a). Wihok separates it, finds the BPM and the key,
and saves the results in `Music\Wihok\<song name>-<short id>\` as `<song>_karaoke.wav` and
`<song>_acapella.wav`. A song you have already processed reuses its earlier results and never
overwrites them.

The window has a light and a dark theme (the first launch follows Windows) and an English / ไทย
switch. Both, and your choice about update checks, are remembered.

## GPU or CPU

| Your computer | What Wihok uses | Example: a 2.5-minute song |
| --- | --- | --- |
| NVIDIA card, with GPU support installed | the GPU | about 9 seconds |
| Any other computer (AMD, Intel, no graphics card) | the CPU | about 70 seconds |

The times were measured on one computer (RTX 3070 Ti, a 12-thread processor); yours will differ.
GPU support is for NVIDIA cards only. AMD and Intel graphics work, on the CPU.

## Updates and privacy

Your audio never leaves your computer. Wihok connects to the internet in two cases:

- **The separation model**, downloaded once the first time you separate a song.
- **Update checks.** A few seconds after it opens, at most once a day, Wihok asks GitHub whether a
  newer release exists. GitHub sees your IP address and that a request came from Wihok; nothing
  else is sent.

To check by hand or to switch the automatic check off, press the arrow button in the title bar.
When a new version is available, a small bar offers **Update**. Pressing it downloads the installer,
checks it against the SHA-256 checksum that GitHub publishes for it, installs it over your current
copy and opens Wihok again. Nothing is installed without your click, and never while a song is being
processed.

## Uninstalling

Use Windows Settings, then Apps. Uninstalling removes the program files. It never deletes
`Music\Wihok`, and it asks before removing Wihok's saved settings.

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

## Fonts

`assets/fonts/TA GBA monothai_MAX.ttf` is by Taweechai Assawarangsitsang (TA Font),
licensed under the SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). It is used
unmodified. It is an experimental pixel font, so some Thai letters are simplified, and it looks
sharpest at 100% display scaling. The banner above is drawn with the same font.

## License

Wihok is released under the MIT License (see `LICENSE`). It uses many open-source libraries,
each under its own license; they are listed with their license texts in
`THIRD-PARTY-NOTICES.txt` (regenerate it with `python packaging/make_notices.py`). The font is
under the SIL Open Font License (`assets/fonts/OFL.txt`). The NVIDIA CUDA libraries inside the GPU
add-on are NVIDIA software and are not covered by the MIT license. The separation model is not
included; see the section above.

---

## วิหค (ภาษาไทย)

ลากเพลงมาวาง ได้แทร็กคาราโอเกะ (เฉพาะดนตรี) แทร็กอะคาเพลลา (เฉพาะเสียงร้อง) พร้อม BPM และ Key
ทำงานในเครื่องของคุณทั้งหมด ไฟล์เสียงไม่ถูกส่งขึ้นอินเทอร์เน็ต และฟังแทร็กต้นฉบับ คาราโอเกะ
และอะคาเพลลาในแอปได้

### ดาวน์โหลด

1. เปิด[หน้า release ล่าสุด](https://github.com/Babyferret/wihok/releases/latest)
2. ดาวน์โหลด `Wihok-Setup-<เวอร์ชัน>.exe` (ประมาณ 190 MB) แล้วเปิดใช้ ไฟล์นี้ไฟล์เดียวพอ
   ถ้าคุณมีการ์ดจอ NVIDIA ตัวติดตั้งจะถามว่าต้องการรองรับการ์ดจอไหม และดาวน์โหลดส่วนเสริมให้เอง
3. Windows อาจขึ้น **"Windows protected your PC"** และบอกว่าไม่ทราบผู้เผยแพร่ เพราะตัวติดตั้งยังไม่ได้
   เซ็นโค้ด ให้กด **More info** แล้ว **Run anyway**

ติดตั้งเฉพาะบัญชีของคุณ จึงไม่ต้องใช้รหัสผ่านผู้ดูแลระบบ

**สิ่งที่ต้องมี:** Windows 10 หรือ 11 (64 บิต) วิหคพัฒนาและทดสอบบน Windows 10 / พื้นที่ดิสก์ประมาณ
0.8 GB (ประมาณ 4 GB ถ้าติดตั้งส่วนรองรับการ์ดจอ) / อินเทอร์เน็ต สำหรับดาวน์โหลดโมเดลแยกเสียงหนึ่งครั้ง
(ประมาณ 80 MB) และสำหรับตรวจสอบการอัปเดต / FFmpeg เฉพาะไฟล์ `.m4a` ส่วน mp3, wav และ flac ไม่ต้องใช้

### การใช้งาน

ลากเพลง (mp3, wav, flac หรือ m4a) มาวางที่หน้าต่าง วิหคจะแยกเสียง หา BPM และ Key แล้วบันทึกผลที่
`Music\Wihok\<ชื่อเพลง>-<รหัสสั้น>\` เป็น `<เพลง>_karaoke.wav` และ `<เพลง>_acapella.wav`
เพลงที่เคยทำแล้วจะใช้ผลเดิม ไม่ทับไฟล์เก่า เลือกธีมสว่าง/มืดและภาษาไทย/อังกฤษได้จากแถบด้านบน
ระบบจำการตั้งค่าเหล่านี้และการเลือกเรื่องตรวจอัปเดตไว้ให้

**การ์ดจอหรือ CPU:** เครื่องที่มีการ์ดจอ NVIDIA และติดตั้งส่วนรองรับการ์ดจอไว้ ใช้การ์ดจอ เพลงยาว 2.5 นาที
ใช้เวลาประมาณ 9 วินาที ส่วนเครื่องอื่น (AMD, Intel หรือไม่มีการ์ดจอ) ใช้ CPU ประมาณ 70 วินาที
(วัดบนเครื่องเดียว เครื่องของคุณอาจต่างกัน) การรองรับการ์ดจอมีเฉพาะ NVIDIA

### การอัปเดตและความเป็นส่วนตัว

ไฟล์เสียงของคุณไม่ออกจากเครื่อง วิหคเชื่อมต่ออินเทอร์เน็ตเพียงสองกรณี คือดาวน์โหลดโมเดลแยกเสียงครั้งแรก
และตรวจสอบการอัปเดต ซึ่งทำอย่างมากวันละครั้ง หลังเปิดแอปไม่กี่วินาที โดยถาม GitHub ว่ามีรุ่นใหม่ไหม
GitHub เห็นที่อยู่ IP ของคุณและเห็นว่ามีคำขอจากวิหค ไม่มีข้อมูลอื่นถูกส่ง

กดปุ่มลูกศรบนแถบหัวข้อเพื่อตรวจสอบด้วยตัวเองหรือปิดการตรวจอัตโนมัติ เมื่อมีรุ่นใหม่ จะมีแถบเล็ก ๆ ให้กด **อัปเดต**
แอปจะดาวน์โหลดตัวติดตั้ง ตรวจกับค่า SHA-256 ที่ GitHub เผยแพร่ ติดตั้งทับของเดิม แล้วเปิดวิหคกลับ
ไม่มีอะไรถูกติดตั้งถ้าคุณไม่กด และไม่ทำขณะกำลังแยกเพลง

### การถอนการติดตั้ง

ใช้ Windows Settings แล้วเลือก Apps การถอนจะลบเฉพาะไฟล์โปรแกรม ไม่ลบ `Music\Wihok` และจะถามก่อนลบการตั้งค่า

### โมเดลแยกเสียง

ผู้สร้าง Demucs ระบุเองว่าใบอนุญาตของน้ำหนักโมเดล "ไม่ชัดเจน" (ข้อมูลฝึกมี MUSDB ที่เดิมใช้ได้เฉพาะงานวิจัย
และอาจเข้าข่ายไม่อนุญาตให้ใช้เชิงพาณิชย์) วิหคจึงไม่แจกจ่ายตัวโมเดล ครั้งแรกที่แยกเสียงแอปจะดาวน์โหลดจาก
หน้าของผู้สร้างเอง (ประมาณ 80 MB ต้องมีอินเทอร์เน็ตหนึ่งครั้ง) ควรใช้ผลลัพธ์เพื่อส่วนตัวและไม่ใช่เชิงพาณิชย์
เว้นแต่คุณตรวจสอบสิทธิ์เอง
