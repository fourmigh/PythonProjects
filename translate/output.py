def export_lines(src_lines, tgt_lines, path):
    n = max(len(src_lines), len(tgt_lines))
    with open(path, 'w', encoding='utf-8-sig') as f:
        for i in range(n):
            s = src_lines[i] if i < len(src_lines) else ''
            t = tgt_lines[i] if i < len(tgt_lines) else ''
            f.write(s + '\n' + t + '\n')
