import sys
import os
import json
import cv2

WINDOW = "ROI Editor"
DEFAULTS = {
    "s_y1": 65,
    "s_y2": 95,
    "w_x1": 65,
    "w_y1": 88,
    "w_x2": 100,
    "w_y2": 100,
}

KEYS = list(DEFAULTS.keys())
_KEY_TO_JSON = {
    "s_y1": "subtitle_y1",
    "s_y2": "subtitle_y2",
    "w_x1": "wm_x1",
    "w_y1": "wm_y1",
    "w_x2": "wm_x2",
    "w_y2": "wm_y2",
}
_JSON_TO_KEY = {v: k for k, v in _KEY_TO_JSON.items()}

_FRAME = None
_CAP = None
_FRAME_IDX = 0
_TOTAL = 0
_PREV_FRAME_POS = -1


def _draw(frame, vals):
    h, w = frame.shape[:2]
    vis = frame.copy()

    sy1 = int(h * vals["s_y1"] / 100)
    sy2 = int(h * vals["s_y2"] / 100)
    cv2.rectangle(vis, (0, sy1), (w, sy2), (0, 0, 255), 2)
    cv2.putText(vis, "subtitle", (3, sy1 + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    wx1 = int(w * vals["w_x1"] / 100)
    wy1 = int(h * vals["w_y1"] / 100)
    wx2 = int(w * vals["w_x2"] / 100)
    wy2 = int(h * vals["w_y2"] / 100)
    cv2.rectangle(vis, (wx1, wy1), (wx2, wy2), (255, 0, 0), 1)
    cv2.putText(vis, "wm", (wx1 + 3, wy1 + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    pct = (_FRAME_IDX / (_TOTAL - 1) * 100) if _TOTAL > 1 else 0
    lines = [
        "frame: {}/{} ({:.1f}%)".format(_FRAME_IDX, _TOTAL, pct),
        "s_y1={} s_y2={}".format(vals["s_y1"], vals["s_y2"]),
        "w_x1={}  w_y1={}  w_x2={}  w_y2={}".format(
            vals["w_x1"], vals["w_y1"], vals["w_x2"], vals["w_y2"]),
        "[s]=save  [q]=quit  [+/-]=step  [drag frame slider]=seek",
    ]
    y0 = 30
    for i, line in enumerate(lines):
        cv2.putText(vis, line, (10, y0 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    return vis


def _on_trackbar(_unused):
    global _FRAME_IDX, _FRAME, _PREV_FRAME_POS
    vals = {}
    for k in KEYS:
        vals[k] = cv2.getTrackbarPos(k, WINDOW)

    if _TOTAL > 1:
        frame_pos = cv2.getTrackbarPos("frame", WINDOW)
        if frame_pos != _PREV_FRAME_POS:
            _PREV_FRAME_POS = frame_pos
            new_idx = int(frame_pos / 1000.0 * (_TOTAL - 1))
            if new_idx != _FRAME_IDX:
                _FRAME_IDX = new_idx
                _CAP.set(cv2.CAP_PROP_POS_FRAMES, _FRAME_IDX)
                ret, frame = _CAP.read()
                if ret:
                    _FRAME = frame

    cv2.imshow(WINDOW, _draw(_FRAME, vals))


def _seek_to(idx):
    global _FRAME_IDX, _FRAME, _PREV_FRAME_POS
    _FRAME_IDX = max(0, min(idx, _TOTAL - 1))
    _CAP.set(cv2.CAP_PROP_POS_FRAMES, _FRAME_IDX)
    ret, frame = _CAP.read()
    if not ret:
        return
    _FRAME = frame
    if _TOTAL > 1:
        _PREV_FRAME_POS = int(_FRAME_IDX / (_TOTAL - 1) * 1000)
        cv2.setTrackbarPos("frame", WINDOW, _PREV_FRAME_POS)
    _on_trackbar(0)


def main():
    global _FRAME, _CAP, _FRAME_IDX, _TOTAL

    if len(sys.argv) < 2:
        print("Usage: python editor.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    _CAP = cv2.VideoCapture(video_path)
    _TOTAL = int(_CAP.get(cv2.CAP_PROP_FRAME_COUNT))
    ret, _FRAME = _CAP.read()
    if not ret:
        print("Cannot read video")
        sys.exit(1)

    out_dir = os.path.dirname(os.path.abspath(video_path))
    config_path = os.path.join(out_dir, "roi_config.json")

    if os.path.exists(config_path):
        with open(config_path) as f:
            saved = json.load(f)
        for json_key, key in _JSON_TO_KEY.items():
            if json_key in saved:
                DEFAULTS[key] = int(saved[json_key] * 100)
        print("Loaded config from {}".format(config_path))

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    for k in KEYS:
        cv2.createTrackbar(k, WINDOW, DEFAULTS[k], 100, _on_trackbar)
    cv2.createTrackbar("frame", WINDOW, 0, 1000, _on_trackbar)

    _on_trackbar(0)

    print("Controls:")
    print("  [trackbars]  drag to adjust ROI")
    print("  [frame]      drag to seek timeline")
    print("  [s]          save config to roi_config.json")
    print("  [q]          quit")
    print("  [+ / =]      next frame       [-]         previous frame")
    print("  []]           skip 10 frames    [[]         back 10 frames")

    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            vals = {}
            for k in KEYS:
                v = cv2.getTrackbarPos(k, WINDOW) / 100.0
                vals[_KEY_TO_JSON[k]] = v
            with open(config_path, 'w') as f:
                json.dump(vals, f, indent=2)
            print("Saved to {}".format(config_path))
        elif key in (ord('+'), ord('=')):
            _seek_to(_FRAME_IDX + 1)
        elif key in (ord('-'), ord('_')):
            _seek_to(_FRAME_IDX - 1)
        elif key in (ord(']'),):
            _seek_to(_FRAME_IDX + 10)
        elif key in (ord('['),):
            _seek_to(_FRAME_IDX - 10)

    _CAP.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
