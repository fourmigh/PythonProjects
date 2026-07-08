import sys
import os
import json
import cv2

WINDOW = "ROI Editor"
HANDLE_R = 8

_VALS = {"s_x1": 0, "s_x2": 100, "s_y1": 65, "s_y2": 95,
          "w_x1": 65, "w_y1": 88, "w_x2": 100, "w_y2": 100}

_KEY_TO_JSON = {
    "s_x1": "subtitle_x1", "s_x2": "subtitle_x2",
    "s_y1": "subtitle_y1", "s_y2": "subtitle_y2",
    "w_x1": "wm_x1", "w_y1": "wm_y1",
    "w_x2": "wm_x2", "w_y2": "wm_y2",
}
_JSON_TO_KEY = {v: k for k, v in _KEY_TO_JSON.items()}

_FRAME = None
_CAP = None
_TOTAL = 0
_FRAME_IDX = 0
_PREV_FRAME_POS = -1
_dragging = None
_hovered = None

_BOXES = [
    ("s", "subtitle", "s_x1", "s_x2", "s_y1", "s_y2"),
    ("w", "wm",       "w_x1", "w_x2", "w_y1", "w_y2"),
]

_TIP_NAMES = {
    "tl": "top-left", "tr": "top-right", "bl": "bot-left", "br": "bot-right",
    "top": "top edge", "bot": "bottom edge",
    "left": "left edge", "right": "right edge",
    "ctr": "center (drag to move)",
}


def _handles(h, w):
    for prefix, _, x1k, x2k, y1k, y2k in _BOXES:
        x1 = int(w * _VALS[x1k] / 100)
        x2 = int(w * _VALS[x2k] / 100)
        y1 = int(h * _VALS[y1k] / 100)
        y2 = int(h * _VALS[y2k] / 100)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        for htype, (hx, hy) in [
            ("tl", (x1, y1)), ("tr", (x2, y1)),
            ("bl", (x1, y2)), ("br", (x2, y2)),
            ("top", (cx, y1)), ("bot", (cx, y2)),
            ("left", (x1, cy)), ("right", (x2, cy)),
            ("ctr", (cx, cy)),
        ]:
            yield ("{}:{}".format(prefix, htype), hx, hy)


def _hit(mx, my, hs):
    for hid, hx, hy in hs:
        if abs(mx - hx) <= HANDLE_R and abs(my - hy) <= HANDLE_R:
            return hid
    return None


def _redraw():
    global _FRAME
    h, w = _FRAME.shape[:2]
    vis = _FRAME.copy()

    for prefix, label, x1k, x2k, y1k, y2k in _BOXES:
        x1 = int(w * _VALS[x1k] / 100)
        x2 = int(w * _VALS[x2k] / 100)
        y1 = int(h * _VALS[y1k] / 100)
        y2 = int(h * _VALS[y2k] / 100)
        color = (0, 0, 255) if prefix == "s" else (255, 0, 0)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, label, (x1 + 3, y1 + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    hs = list(_handles(h, w))
    for hid, hx, hy in hs:
        prefix = hid[0]
        if _dragging == hid:
            c = (0, 255, 255)
        elif _hovered == hid:
            c = (0, 255, 0)
        elif prefix == "s":
            c = (10, 200, 200)
        else:
            c = (200, 200, 10)
        cv2.circle(vis, (hx, hy), HANDLE_R, c, -1)
        cv2.circle(vis, (hx, hy), HANDLE_R, (180, 180, 180), 1)

        if _hovered == hid:
            _, htype = hid.split(":")
            _, label, _, _, _, _ = _BOXES[0] if prefix == "s" else _BOXES[1]
            tip = "{} {}".format(label, _TIP_NAMES.get(htype, htype))
            tx, ty = hx + 14, hy - 8
            cv2.putText(vis, tip, (tx, ty),
                        cv2.FONT_HERSHEY_PLAIN, 1.2, (20, 20, 20), 3)
            cv2.putText(vis, tip, (tx, ty),
                        cv2.FONT_HERSHEY_PLAIN, 1.2, (0, 255, 0), 1)

    pct = (_FRAME_IDX / (_TOTAL - 1) * 100) if _TOTAL > 1 else 0
    lines = [
        "frame: {}/{} ({:.1f}%)".format(_FRAME_IDX, _TOTAL, pct),
        "s_x1={} s_x2={} s_y1={} s_y2={}".format(
            _VALS["s_x1"], _VALS["s_x2"], _VALS["s_y1"], _VALS["s_y2"]),
        "w_x1={} w_y1={} w_x2={} w_y2={}".format(
            _VALS["w_x1"], _VALS["w_y1"], _VALS["w_x2"], _VALS["w_y2"]),
        "[s]save [q]quit [+/-]step [[]]skip10  drag handles to resize",
    ]
    for i, line in enumerate(lines):
        cv2.putText(vis, line, (10, 30 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imshow(WINDOW, vis)


def _on_mouse(event, x, y, flags, _):
    global _dragging, _hovered
    h, w = _FRAME.shape[:2]
    hs = list(_handles(h, w))

    if event == cv2.EVENT_MOUSEMOVE:
        if _dragging:
            _apply_drag(x, y, h, w)
        else:
            prev = _hovered
            _hovered = _hit(x, y, hs)
            if _hovered != prev:
                print("[hover] {}".format(_hovered))
            _redraw()
    elif event == cv2.EVENT_LBUTTONDOWN:
        hit = _hit(x, y, hs)
        if hit:
            _dragging = hit
            _hovered = hit
            _redraw()
    elif event == cv2.EVENT_LBUTTONUP:
        _dragging = None
        _hovered = None
        _redraw()


def _apply_drag(mx, my, h, w):
    prefix, htype = _dragging.split(":")
    px = max(0, min(100, round(mx / w * 100)))
    py = max(0, min(100, round(my / h * 100)))
    v = _VALS
    keys = {k: k for _, _, k, _, _, _ in _BOXES}  # map x1k->x1k, etc.
    # Build key map for this prefix
    x1k = "{}_x1".format(prefix)
    x2k = "{}_x2".format(prefix)
    y1k = "{}_y1".format(prefix)
    y2k = "{}_y2".format(prefix)

    if htype == "tl":
        v[x1k], v[y1k] = min(px, v[x2k] - 1), min(py, v[y2k] - 1)
    elif htype == "tr":
        v[x2k], v[y1k] = max(px, v[x1k] + 1), min(py, v[y2k] - 1)
    elif htype == "bl":
        v[x1k], v[y2k] = min(px, v[x2k] - 1), max(py, v[y1k] + 1)
    elif htype == "br":
        v[x2k], v[y2k] = max(px, v[x1k] + 1), max(py, v[y1k] + 1)
    elif htype == "top":
        v[y1k] = min(py, v[y2k] - 1)
    elif htype == "bot":
        v[y2k] = max(py, v[y1k] + 1)
    elif htype == "left":
        v[x1k] = min(px, v[x2k] - 1)
    elif htype == "right":
        v[x2k] = max(px, v[x1k] + 1)
    elif htype == "ctr":
        dw = v[x2k] - v[x1k]
        dh = v[y2k] - v[y1k]
        nx1 = max(0, min(100 - dw, px - dw // 2))
        ny1 = max(0, min(100 - dh, py - dh // 2))
        v[x1k], v[y1k] = nx1, ny1
        v[x2k], v[y2k] = nx1 + dw, ny1 + dh

    _redraw()


def _on_frame(pos):
    global _FRAME_IDX, _FRAME, _PREV_FRAME_POS
    if _TOTAL <= 1 or pos == _PREV_FRAME_POS:
        return
    _PREV_FRAME_POS = pos
    _FRAME_IDX = int(pos / 1000.0 * (_TOTAL - 1))
    _CAP.set(cv2.CAP_PROP_POS_FRAMES, _FRAME_IDX)
    ret, frame = _CAP.read()
    if ret:
        _FRAME = frame
        _redraw()


def _seek(idx):
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
    _redraw()


def main():
    global _FRAME, _CAP, _TOTAL, _FRAME_IDX
    if len(sys.argv) < 2:
        print("Usage: python editor.py <video_path>")
        sys.exit(1)

    vp = sys.argv[1]
    _CAP = cv2.VideoCapture(vp)
    _TOTAL = int(_CAP.get(cv2.CAP_PROP_FRAME_COUNT))
    ret, _FRAME = _CAP.read()
    if not ret:
        print("Cannot read video")
        sys.exit(1)

    cfg = os.path.join(os.path.dirname(os.path.abspath(vp)), "roi_config.json")
    if os.path.exists(cfg):
        with open(cfg) as f:
            saved = json.load(f)
        for jk, k in _JSON_TO_KEY.items():
            if jk in saved:
                _VALS[k] = int(saved[jk] * 100)
        print("Loaded config from {}".format(cfg))

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    cv2.createTrackbar("frame", WINDOW, 0, 1000, _on_frame)
    cv2.setMouseCallback(WINDOW, _on_mouse)
    _redraw()

    print("Controls:")
    print("  drag handles   resize ROI boxes")
    print("  [frame] slider seek timeline")
    print("  [s]            save roi_config.json")
    print("  [q]            quit")
    print("  [+ =] next     [-] prev     [[]] back10     []]] fwd10")

    while True:
        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            vals = {_KEY_TO_JSON[k]: _VALS[k] / 100.0 for k in _VALS}
            with open(cfg, 'w') as f:
                json.dump(vals, f, indent=2)
            print("Saved to {}".format(cfg))
        elif key in (ord('+'), ord('=')):
            _seek(_FRAME_IDX + 1)
        elif key in (ord('-'), ord('_')):
            _seek(_FRAME_IDX - 1)
        elif key == ord(']'):
            _seek(_FRAME_IDX + 10)
        elif key == ord('['):
            _seek(_FRAME_IDX - 10)

    _CAP.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
