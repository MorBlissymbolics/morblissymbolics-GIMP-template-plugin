#!/usr/bin/env python3
# MorBlissymbolics Template — GIMP 3.x Python plug-in.
#
# Modeled on mor-dictionary-entry-template: same profiles.json schema,
# same optional multi-line pattern (Definition / Definition Line 2 /
# Definition Line 3, Etymology / Etymology Line 2 / Etymology Line 3),
# same offset_x_ratio / layer_width_ratio / offset_y_ratio layout logic.
#
# Layout adds one new section: a Blissymbol SVG/PNG placed to the left
# of the text column (landscape) or above it (portrait/TikTok).
#
# Install:
#   ~/.config/GIMP/3.2/plug-ins/mor-blissymbolics-template/
#       mor-blissymbolics-template.py   (chmod +x)
#       profiles.json                   (same folder)

import json
import os
import sys

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
from gi.repository import Gimp, GimpUi, GObject, GLib, Gio

PROC_NAME   = 'plug-in-mor-blissymbolics-template'
PROFILE_KEY = 'profiles.json'

# ── built-in fallback profiles ────────────────────────────────────────────────
BUILTIN = {
    "profiles": [
        {
            "key": "hd_landscape",
            "name": "HD Landscape (1920 x 1080)",
            "height_min": 1060, "height_max": 1100,
            "layout": "side",
            # text sizes (Pango points)
            "hw_size": 64, "pos_size": 22, "ety_size": 26, "df_size": 24,
            # rises
            "hw_rise": 0, "ety_rise": 0, "df_rise": 0,
            # gaps (points, converted to px via dpi)
            "gap_after_headword": 6, "gap_after_pos": 8,
            "gap_after_etymology": 14, "gap_after_definition": 0,
            # dividers (box-drawing chars, 0 = off)
            "div_after_word": 0, "div_after_pos": 1, "div_after_etymology": 0,
            # text column geometry
            "offset_x_ratio": 0.42, "offset_y_ratio": 0.03,
            "layer_width_ratio": 0.55,
            # symbol geometry
            "symbol_center_x_ratio": 0.21,
            "symbol_max_w_ratio": 0.32, "symbol_max_h_ratio": 0.50,
            # misc
            "chars_per_line": 38,
            "default_font": "IM FELL English Regular",
            "notes": "1920x1080. Symbol left, text right."
        },
        {
            "key": "tiktok",
            "name": "TikTok / Reels (1080 x 1920)",
            "height_min": 1840, "height_max": 2000,
            "layout": "stacked",
            "hw_size": 84, "pos_size": 30, "ety_size": 36, "df_size": 34,
            "hw_rise": 0, "ety_rise": 0, "df_rise": 0,
            "gap_after_headword": 10, "gap_after_pos": 14,
            "gap_after_etymology": 22, "gap_after_definition": 0,
            "div_after_word": 0, "div_after_pos": 1, "div_after_etymology": 0,
            "offset_x_ratio": 0.08, "offset_y_ratio": 0.03,
            "layer_width_ratio": 0.84,
            "symbol_top_ratio": 0.10,
            "symbol_max_w_ratio": 0.72, "symbol_max_h_ratio": 0.22,
            "gap_after_symbol": 60,
            "chars_per_line": 28,
            "default_font": "IM FELL English Regular",
            "notes": "1080x1920. Symbol top, text centered below."
        },
        {
            "key": "custom",
            "name": "Custom / Fallback (ratio-based)",
            "height_min": 0, "height_max": 999999,
            "layout": "auto",
            "hw_ratio": 0.060, "pos_ratio": 0.020,
            "ety_ratio": 0.026, "df_ratio": 0.024,
            "hw_rise": 0, "ety_rise": 0, "df_rise": 0,
            "gap_hw_ratio": 0.007, "gap_pos_ratio": 0.010,
            "gap_ety_ratio": 0.014, "gap_df_ratio": 0.000,
            "div_after_word": 0, "div_after_pos": 0, "div_after_etymology": 0,
            "offset_x_ratio": 0.42, "offset_y_ratio": 0.04,
            "layer_width_ratio": 0.55,
            "symbol_center_x_ratio": 0.21,
            "symbol_top_ratio": 0.10,
            "symbol_max_w_ratio": 0.32, "symbol_max_h_ratio": 0.45,
            "gap_after_symbol": 0,
            "gap_symbol_ratio": 0.04,
            "chars_per_line": 36,
            "default_font": "IM FELL English Regular",
            "notes": "Ratio fallback. layout=auto picks side/stacked by aspect ratio."
        }
    ]
}

# ── profile helpers ───────────────────────────────────────────────────────────

def _profile_paths():
    here = os.path.dirname(os.path.realpath(__file__))
    return [
        os.path.join(here, PROFILE_KEY),
        os.path.join(GLib.get_user_config_dir(), 'morblissymbolics', PROFILE_KEY),
    ]

def load_profiles():
    for path in _profile_paths():
        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                if isinstance(data, dict) and data.get('profiles'):
                    return data, path
        except Exception as exc:
            Gimp.message(f"MorBlissymbolics: could not read {path}: {exc}")
    return BUILTIN, '<built-in defaults>'

def pick_profile(data, height):
    fallback = None
    for p in data.get('profiles', []):
        if p.get('key') == 'custom':
            fallback = p
            continue
        if p.get('height_min', 0) <= height <= p.get('height_max', 10**9):
            return p
    return fallback or data['profiles'][-1]

def resolve(prof, width, height):
    """Materialise ratio-based fields for the custom/fallback profile."""
    p = dict(prof)
    def r(key, base):
        return p[key] * base if key in p else None

    if 'hw_size' not in p:
        p['hw_size']  = r('hw_ratio',  height) or height * 0.060
        p['pos_size'] = r('pos_ratio', height) or height * 0.020
        p['ety_size'] = r('ety_ratio', height) or height * 0.026
        p['df_size']  = r('df_ratio',  height) or height * 0.024
        p['gap_after_headword']  = (r('gap_hw_ratio',  height) or 0)
        p['gap_after_pos']       = (r('gap_pos_ratio', height) or 0)
        p['gap_after_etymology'] = (r('gap_ety_ratio', height) or 0)
        p['gap_after_definition']= (r('gap_df_ratio',  height) or 0)
        p['gap_after_symbol']    = (r('gap_symbol_ratio', height) or height * 0.04)

    if p.get('layout', 'auto') == 'auto':
        p['layout'] = 'side' if width >= height else 'stacked'

    p.setdefault('div_after_word', 0)
    p.setdefault('div_after_pos', 0)
    p.setdefault('div_after_etymology', 0)
    p.setdefault('gap_after_symbol', height * 0.04)
    p.setdefault('symbol_center_x_ratio', 0.21)
    p.setdefault('symbol_top_ratio', 0.10)
    p.setdefault('symbol_max_w_ratio', 0.32)
    p.setdefault('symbol_max_h_ratio', 0.45)
    p.setdefault('chars_per_line', 36)
    p.setdefault('hw_rise', 0)
    p.setdefault('ety_rise', 0)
    p.setdefault('df_rise', 0)
    return p

# ── CJK-aware display width ───────────────────────────────────────────────────

def _dw(s):
    """Return display-column width of string s (CJK = 2 cols, else 1)."""
    w = 0
    for ch in s:
        cp = ord(ch)
        if (0x1100 <= cp <= 0x11FF or 0x2E80 <= cp <= 0x303F or
                0x3040 <= cp <= 0xA4CF or 0xAC00 <= cp <= 0xD7AF or
                0xF900 <= cp <= 0xFAFF or 0xFE10 <= cp <= 0xFE6F or
                0xFF00 <= cp <= 0xFFEF or 0x1B000 <= cp <= 0x1B0FF or
                0x20000 <= cp <= 0x2CEAF):
            w += 2
        else:
            w += 1
    return w

# ── misc helpers ──────────────────────────────────────────────────────────────

def get_dpi(image):
    try:
        res = image.get_resolution()
        nums = [float(v) for v in (res if isinstance(res, (list, tuple)) else [res])
                if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums:
            return nums[-1]
    except Exception:
        pass
    return 72.0

def pango_pt(pts):
    return int(round(pts * 1024))

def resolve_font(cfg_font, prof):
    if cfg_font is not None:
        return cfg_font
    name = prof.get('default_font')
    if name:
        try:
            f = Gimp.Font.get_by_name(name)
            if f:
                return f
        except Exception:
            pass
    return Gimp.context_get_font()

# ── GIMP layer helpers ────────────────────────────────────────────────────────

def text_layer(image, font, size_pt, markup, name, centered=False):
    lay = Gimp.TextLayer.new(image, ' ', font, size_pt, Gimp.Unit.point())
    image.insert_layer(lay, None, -1)
    lay.set_markup(markup)
    if centered:
        try:
            lay.set_justification(Gimp.TextJustification.CENTER)
        except Exception:
            pass
    try:
        lay.set_color(Gimp.context_get_foreground())
    except Exception:
        pass
    lay.set_name(name)
    return lay

def load_symbol(image, path):
    gfile = Gio.File.new_for_path(path)
    lay = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, gfile)
    image.insert_layer(lay, None, -1)
    lay.set_name('blissymbol')
    return lay

def fit_symbol(lay, box_w, box_h):
    lw, lh = lay.get_width(), lay.get_height()
    if lw <= 0 or lh <= 0:
        return
    scale = min(box_w / lw, box_h / lh)
    lay.scale(max(1, int(lw * scale)), max(1, int(lh * scale)), False)

# ── markup builders ───────────────────────────────────────────────────────────

def esc(s):
    return GLib.markup_escape_text(s)

def font_name(font):
    """Get a font's display name across GIMP 3.x variants."""
    for getter in ('get_name',):
        try:
            fn = getattr(font, getter, None)
            if fn:
                n = fn()
                if n:
                    return n
        except Exception:
            pass
    try:
        return Gimp.Resource.get_name(font)
    except Exception:
        return 'Sans'

def span(text, font, size_pt, italic=False, rise=0):
    attrs = f"font_desc='{esc(font_name(font))} {int(size_pt)}'"
    if rise:
        attrs += f" rise='{pango_pt(rise)}'"
    inner = f'<i>{esc(text)}</i>' if italic else esc(text)
    return f'<span {attrs}>{inner}</span>'

def draw_divider_layer(image, width_px, thickness_px, name='divider'):
    """Create a full-canvas transparent layer with a horizontal rule drawn
    into it, `width_px` wide and `thickness_px` tall, top-left at (0,0).
    The caller repositions it with set_offsets, then the rule sits at the
    layer's top-left corner. Returns the layer (its own size = the rule)."""
    thickness_px = max(1, int(thickness_px))
    width_px = max(1, int(width_px))
    lay = Gimp.Layer.new(image, name, width_px, thickness_px,
                         Gimp.ImageType.RGBA_IMAGE, 100.0,
                         Gimp.LayerMode.NORMAL)
    image.insert_layer(lay, None, -1)
    lay.fill(Gimp.FillType.TRANSPARENT)
    image.select_rectangle(Gimp.ChannelOps.REPLACE, 0, 0,
                           width_px, thickness_px)
    Gimp.Drawable.edit_fill(lay, Gimp.FillType.FOREGROUND)
    Gimp.Selection.none(image)
    return lay

# ── layout ────────────────────────────────────────────────────────────────────

def render(image, font, prof,
           headword, pos,
           ety1, ety2, ety3,
           df1, df2, df3,
           symbol_path):

    w, h   = image.get_width(), image.get_height()
    dpi    = get_dpi(image)
    pt2px  = dpi / 72.0
    layout = prof['layout']
    stacked = (layout == 'stacked')

    # ── blissymbol ────────────────────────────────────────────────────────────
    symbol = None
    if symbol_path:
        try:
            symbol = load_symbol(image, symbol_path)
            fit_symbol(symbol,
                       w * prof['symbol_max_w_ratio'],
                       h * prof['symbol_max_h_ratio'])
        except Exception as exc:
            Gimp.message(f"MorBlissymbolics: symbol load failed: {exc}")

    # ── build entry list ──────────────────────────────────────────────────────
    # Each entry is a dict describing one row:
    #   {'kind': 'text',    'layer': <TextLayer>, 'gap': px}
    #   {'kind': 'divider', 'gap': px}   ← width/thickness resolved after
    #                                       we know the text column width
    def gap(pts):
        return pts * pt2px

    entries = []

    # headword + pos on same line
    if headword:
        m = span(headword, font, prof['hw_size'], rise=prof.get('hw_rise', 0))
        if pos:
            m += '  ' + span(pos, font, prof['pos_size'])
        lay = text_layer(image, font, prof['hw_size'], m, 'headword',
                         centered=stacked)
        entries.append({'kind': 'text', 'layer': lay,
                        'gap': gap(prof['gap_after_headword'])})

    if prof.get('div_after_word'):
        entries.append({'kind': 'divider',
                        'gap': gap(prof.get('gap_after_pos', 8))})

    # etymology lines
    ety_lines = [l for l in [ety1, ety2, ety3] if l and l.strip()]
    for i, line in enumerate(ety_lines):
        is_last = (i == len(ety_lines) - 1)
        g = gap(prof['gap_after_etymology']) if is_last else gap(4)
        lay = text_layer(image, font, prof['ety_size'],
                         span(line, font, prof['ety_size'], italic=True,
                              rise=prof.get('ety_rise', 0)),
                         f'etymology_{i+1}', centered=stacked)
        entries.append({'kind': 'text', 'layer': lay, 'gap': g})

    if prof.get('div_after_pos') and (headword or ety_lines):
        entries.append({'kind': 'divider',
                        'gap': gap(prof.get('gap_after_pos', 8))})

    # definition lines
    df_lines = [l for l in [df1, df2, df3] if l and l.strip()]
    for i, line in enumerate(df_lines):
        is_last = (i == len(df_lines) - 1)
        g = gap(prof['gap_after_definition']) if is_last else gap(4)
        lay = text_layer(image, font, prof['df_size'],
                         span(line, font, prof['df_size'],
                              rise=prof.get('df_rise', 0)),
                         f'definition_{i+1}', centered=stacked)
        entries.append({'kind': 'text', 'layer': lay, 'gap': g})

    if prof.get('div_after_etymology'):
        entries.append({'kind': 'divider',
                        'gap': gap(prof.get('gap_after_definition', 4))})

    # park text layers off-canvas while we compute geometry
    for e in entries:
        if e['kind'] == 'text':
            lay = e['layer']
            lay.set_offsets(-lay.get_width() * 2 - 10, -lay.get_height() * 2 - 10)

    # ── divider width ──────────────────────────────────────────────────────────
    # Default: match the widest text row (so the rule spans the definition),
    # capped at layer_width_ratio of the canvas. If the profile sets
    # divider_width_ratio, that fraction of the canvas width wins instead.
    text_widths = [e['layer'].get_width() for e in entries if e['kind'] == 'text']
    col_cap = w * prof.get('layer_width_ratio', 0.55)
    if 'divider_width_ratio' in prof:
        divider_w = w * prof['divider_width_ratio']
    elif text_widths:
        divider_w = min(max(text_widths), col_cap)
    else:
        divider_w = col_cap
    # thickness: explicit px override, else scale to definition font size
    divider_thick = prof.get('divider_thickness',
                             max(2, int(prof.get('df_size', 24) * pt2px * 0.05)))

    # realise divider layers now that we know the width
    for e in entries:
        if e['kind'] == 'divider':
            e['layer'] = draw_divider_layer(image, divider_w, divider_thick)
            # park off-canvas too
            e['layer'].set_offsets(-divider_w * 2 - 10, -10)

    def row_h(e):
        return e['layer'].get_height()

    total_h = sum(row_h(e) + e['gap'] for e in entries)
    if entries:
        total_h -= entries[-1]['gap']  # no trailing gap

    # ── place everything ──────────────────────────────────────────────────────
    if layout == 'side':
        if symbol:
            sx = int(w * prof['symbol_center_x_ratio'] - symbol.get_width() / 2)
            sy = int((h - symbol.get_height()) / 2)
            symbol.set_offsets(max(0, sx), max(0, sy))

        margin_y = h * 0.03
        y = (h - total_h) / 2
        y = max(margin_y, min(y, h - total_h - margin_y))
        text_x = int(w * prof['offset_x_ratio'])
        for e in entries:
            e['layer'].set_offsets(text_x, int(y))   # dividers align to text left
            y += row_h(e) + e['gap']

    else:
        margin_y = h * 0.03
        y = h * prof['symbol_top_ratio']
        if symbol:
            sx = int((w - symbol.get_width()) / 2)
            symbol.set_offsets(max(0, sx), int(y))
            y += symbol.get_height() + prof['gap_after_symbol'] * pt2px

        leftover = h - y - total_h - margin_y
        if leftover > 0:
            y += leftover * 0.30
        y = max(y, h * prof['symbol_top_ratio'])

        for e in entries:
            cx = int((w - e['layer'].get_width()) / 2)   # dividers center too
            e['layer'].set_offsets(cx, int(y))
            y += row_h(e) + e['gap']

# ── plug-in class ─────────────────────────────────────────────────────────────

class MorBliss(Gimp.PlugIn):

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        proc = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        proc.set_image_types('*')
        proc.set_menu_label('MorBlissymbolics Template...')
        proc.add_menu_path('<Image>/Filters/Render/')
        proc.set_documentation(
            'Lay out a Blissymbolics learning card',
            'Adds a blissymbol image, headword, part of speech, up to three '
            'etymology lines, and up to three definition lines to the current '
            'image. Profile (sizes, gaps, layout) is read from profiles.json '
            'next to the plug-in each run.',
            name)
        proc.set_attribution('mor', 'mor', '2026')

        S = GObject.ParamFlags.READWRITE

        proc.add_string_argument('headword',    'Headword',         'e.g. actor',                        'actor',                        S)
        proc.add_string_argument('pos',         'Part of speech',   'e.g. noun  (blank to omit)',        'noun',                         S)
        proc.add_string_argument('etymology_1', 'Etymology',        'First etymology / decomposition line', '(person + play_(theatre))', S)
        proc.add_string_argument('etymology_2', 'Etymology Line 2', 'Second etymology line (optional)',   '',                             S)
        proc.add_string_argument('etymology_3', 'Etymology Line 3', 'Third etymology line (optional)',    '',                             S)
        proc.add_string_argument('definition_1','Definition',       'First definition line',             'A person who performs in plays, films, or other dramatic productions.', S)
        proc.add_string_argument('definition_2','Definition Line 2','Second definition line (optional)', '',                             S)
        proc.add_string_argument('definition_3','Definition Line 3','Third definition line (optional)',  '',                             S)
        proc.add_file_argument(
            'symbol_file', 'Blissymbol file',
            'SVG or PNG blissymbol to place on the card',
            Gimp.FileChooserAction.OPEN, True, None, S)
        proc.add_font_argument(
            'font', 'Font',
            'Font for all text (profile default if left unset)',
            True, None, True, S)

        return proc

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init(PROC_NAME)
            dlg = GimpUi.ProcedureDialog.new(procedure, config,
                                             'MorBlissymbolics Template')
            dlg.fill(None)
            ok = dlg.run()
            dlg.destroy()
            if not ok:
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL, GLib.Error())

        def s(key):
            v = config.get_property(key)
            return (v or '').strip() if isinstance(v, str) else ''

        headword    = s('headword')
        pos         = s('pos')
        ety1        = s('etymology_1')
        ety2        = s('etymology_2')
        ety3        = s('etymology_3')
        df1         = s('definition_1')
        df2         = s('definition_2')
        df3         = s('definition_3')
        sym_gfile   = config.get_property('symbol_file')
        sym_path    = sym_gfile.peek_path() if sym_gfile else None

        data, src  = load_profiles()
        w, h       = image.get_width(), image.get_height()
        prof       = resolve(pick_profile(data, h), w, h)
        font       = resolve_font(config.get_property('font'), prof)

        image.undo_group_start()
        try:
            render(image, font, prof,
                   headword, pos,
                   ety1, ety2, ety3,
                   df1, df2, df3,
                   sym_path)
        except Exception as exc:
            image.undo_group_end()
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                GLib.Error.new_literal(
                    GLib.quark_from_string(PROC_NAME), str(exc), 0))
        image.undo_group_end()
        Gimp.displays_flush()
        Gimp.message(
            f"MorBlissymbolics: used profile '{prof.get('name', prof.get('key', '?'))}'"
            f" from {src}")
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS,
                                           GLib.Error())

Gimp.main(MorBliss.__gtype__, sys.argv)
