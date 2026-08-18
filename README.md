# AutoDraw + adbtouch

**Record what you do on an Android phone, replay it later, and draw images on it — all over USB with no app installed on the device.**

[![CI](https://github.com/MAXAWER/AutoDraw-Sim/actions/workflows/ci.yml/badge.svg)](https://github.com/MAXAWER/AutoDraw-Sim/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![Windows | macOS | Linux](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

This repository is two things:

- **`adbtouch`** — a small Python library for fast synthetic touch input on Android over ADB. Records gestures, replays them, and drives raw `/dev/input` events. Pure standard library; no dependencies for the core.
- **`AutoDraw`** — a desktop app built on it, for people who would rather click buttons than write code.

---

## Why this exists

`adb shell input tap` spawns a process on the device for every single call. At
100–300 ms each, anything continuous — a gesture, a drawn line, a test script —
is unusably slow.

`adbtouch` writes raw kernel input events into `/dev/input` through **one** pushed
shell script instead. A stroke that takes 40 seconds through `input swipe`
finishes in well under a second. That single difference is what makes both
gesture replay and image drawing practical.

---

## Two things it does

### 1. Record and replay gestures

Press record, do something on the phone, press stop. You get a JSON file with
every touch event and its timing. Replay it whenever you want, at whatever speed.

Useful for regression passes (capture a login flow once, run it against every
build), for reproducing a bug reliably, or for any repetitive tapping you would
rather not do by hand.

```bash
adbtouch record -o login.json      # do the thing on the phone, press Enter
adbtouch play login.json --speed 2 --repeat 5
```

### 2. Draw an image on the screen

Load a picture, position it over a preview of the phone screen, press draw. The
image is traced into strokes and drawn with raw touch events.

---

## Install

You need [Android platform-tools](https://developer.android.com/tools/releases/platform-tools)
(`adb`) on your `PATH`, and USB debugging enabled on the phone:
Settings → About phone → tap *Build number* seven times → Developer options →
*USB debugging*.

```bash
git clone https://github.com/MAXAWER/AutoDraw-Sim.git
cd AutoDraw-Sim

# library only - no dependencies at all
pip install -e .

# library + image drawing
pip install -e ".[draw]"

# everything, including the desktop app
pip install -e ".[gui]"
```

Then:

```bash
autodraw              # desktop app
adbtouch --help       # command line
```

If `adb` is installed somewhere unusual, point `ADB_PATH` at it.

---

## Command line

```bash
adbtouch devices                       # what is attached
adbtouch info                          # screen size and digitizer ranges
adbtouch record -o session.json        # record until Enter
adbtouch record -o session.json -d 30  # record for 30 seconds
adbtouch play session.json             # replay once
adbtouch play session.json --speed 0.5 --repeat 3
```

## Library

```python
from adbtouch import Device, Recorder, Session, replay

device = Device()
print(device.screen_size, device.touch_device.path)

recorder = Recorder(device)
recorder.start()
input("Do something on the phone, then press Enter...")
recorder.stop().save("flow.json")

replay(device, Session.load("flow.json"), speed=2.0, repeat=10)
```

Drawing paths directly, in display pixels:

```python
device.draw_paths([[(100, 200), (400, 200), (400, 600)]])
```

---

## How it works

**Batched events.** Every stroke becomes a list of `sendevent` lines, written to a
temporary script, pushed once to `/data/local/tmp`, executed, and deleted. One ADB
round trip instead of thousands.

**Coordinate translation.** The touchscreen digitizer has its own coordinate
space, and on many phones it is *not* the display resolution — a 1080-pixel-wide
screen commonly sits on a 4096-step digitizer. Sending display pixels straight to
`sendevent` puts the touch in the wrong place. `adbtouch` reads the real axis
ranges from `getevent -pl` and rescales. Run `adbtouch info` to see yours.

**Retrace removal.** `findContours` walks the *boundary* of a region, and Canny
turns one pen stroke into two parallel edges — so the naive path traces up one
side of every line and back down the other, drawing everything twice.
`dedupe_retrace` detects when a contour's two halves are the same stroke and keeps
one of them, while leaving genuine closed shapes like circles intact.

---

## Known limits

- **Recordings are not portable between phones.** They contain raw digitizer
  coordinates, so replaying a recording made on a different panel is refused
  rather than silently misfiring.
- **Rotation is not handled.** Record and replay in the same orientation.
- **Some devices need root for `sendevent`.** Most do not; if raw input is
  unavailable the slower `input swipe` path still works.
- **`adbtouch info` is the first thing to check** when touches land in the wrong
  place.

---

## Open ends

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Things worth doing:

- Auto-detect swapped X/Y axes (the `swap_xy` flag exists but nothing sets it).
- Rotation-aware coordinate mapping.
- Trim recordings visually in the app; cut dead time at the start and end.
- Assertions during replay — wait for a screenshot to match before continuing,
  which is what turns this into a real test runner.
- Skeletonise edges instead of halving contours, for cleaner line art.
- Pressure-sensitive strokes from image darkness.

---

## License

MIT — see [LICENSE](LICENSE).

---

<details>
<summary><b>По-русски</b></summary>

## Что это

Две вещи в одном репозитории:

- **`adbtouch`** — библиотека для быстрого синтетического ввода касаний на Android
  через ADB. Записывает жесты, воспроизводит их, работает с событиями
  `/dev/input` напрямую. Ядро не требует зависимостей.
- **`AutoDraw`** — десктопное приложение поверх неё.

## Зачем

`adb shell input tap` запускает отдельный процесс на устройстве при каждом
вызове — 100–300 мс на команду. Для чего-либо непрерывного это неприемлемо
медленно. `adbtouch` пишет события ядра напрямую через **один** сценарий,
загруженный на устройство. Штрих, который через `input swipe` рисуется 40 секунд,
здесь занимает меньше секунды.

## Возможности

**Запись и воспроизведение.** Нажали «запись», сделали что-то на телефоне,
остановили — получили JSON со всеми событиями и таймингами. Воспроизводите когда
угодно и с какой угодно скоростью. Удобно для регрессионного тестирования:
записали сценарий логина один раз, прогоняете на каждой сборке.

**Рисование изображений.** Загрузили картинку, поставили её на превью экрана
телефона, нажали «рисовать».

## Установка

Нужны [platform-tools](https://developer.android.com/tools/releases/platform-tools)
(`adb`) и включённая отладка по USB (Настройки → О телефоне → семь раз по «Номер
сборки» → Для разработчиков → Отладка по USB).

```bash
git clone https://github.com/MAXAWER/AutoDraw-Sim.git
cd AutoDraw-Sim
pip install -e ".[gui]"   # всё вместе
autodraw                  # запуск приложения
```

Если `adb` установлен в нестандартное место — укажите путь в переменной
окружения `ADB_PATH`.

## Командная строка

```bash
adbtouch devices                  # какие устройства подключены
adbtouch info                     # разрешение экрана и диапазоны тачскрина
adbtouch record -o session.json   # запись до нажатия Enter
adbtouch play session.json --speed 2 --repeat 5
```

## Ограничения

- Записи **не переносятся между разными телефонами** — внутри сырые координаты
  тачскрина. Попытка воспроизвести запись на панели другого размера будет
  отклонена, а не выполнена криво.
- Поворот экрана не учитывается: записывайте и воспроизводите в одной ориентации.
- На части устройств `sendevent` требует root. Если сырой ввод недоступен,
  остаётся более медленный путь через `input swipe`.
- Если касания попадают не туда — начните с `adbtouch info`.

## Помощь проекту

См. [CONTRIBUTING.md](CONTRIBUTING.md). Список открытых задач — в разделе
«Open ends» выше. Отчёты о работе на конкретных моделях телефонов тоже полезны:
диапазоны координат тачскрина различаются, и починить можно только то, что видно.

</details>
