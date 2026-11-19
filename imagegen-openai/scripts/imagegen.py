#!/usr/bin/env python3
"""Discover models, generate/edit images, stream, and use Responses/Batch. Python 3.8+."""

import argparse
import base64
import binascii
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib

BASE_ENV = 'IMAGEGEN_OPENAI_API_BASE_URL'
KEY_ENV = 'IMAGEGEN_OPENAI_API_KEY'
DEFAULT_BASE = 'https://api.openai.com/v1'
USER_AGENT = 'imagegen-openai/1.0'
FAMILIES_26 = ('gpt-image-2.6-sunburst', 'gpt-image-2.6-flare')
FAMILIES = FAMILIES_26 + ('gpt-image-2.5-sunburst', 'gpt-image-2.5-flare',
            'gpt-image-2', 'gpt-image-1.5')
PROFILES = {family: {
    'quality': ['auto', 'low', 'medium', 'high'] + (['xhigh', 'max'] if '2.5' in family else []),
    'custom_size': None if family in FAMILIES_26 else family != 'gpt-image-1.5',
    'input_fidelity': ['low', 'high'] if family == 'gpt-image-1.5' else [],
    'markup': '2.5' in family or family in FAMILIES_26,
    'complexity': ['low', 'medium', 'high'] if family in FAMILIES_26 else [],
    'output_formats': ['png', 'jpeg', 'webp'] + (['svg', 'gif'] if family in FAMILIES_26 else []),
    'responses_image_tool_documented': True,
    'transparent_background': 'preview' if family == 'gpt-image-2' else 'supported',
    'image_batch_documented': '2.5' in family,
    'generation': True, 'editing': True, 'streaming': True,
} for family in FAMILIES}
FIELDS = {'model', 'prompt', 'n', 'size', 'quality', 'output_format',
          'background', 'output_compression', 'moderation', 'safety_identifier',
          'stream', 'partial_images', 'user', 'complexity',
          'frame_count', 'frame_duration_ms', 'svg'}
EDIT_FIELDS = {'images', 'mask', 'markup', 'input_fidelity'}
TOOL_FIELDS = {'type', 'model', 'action', 'background', 'input_fidelity',
               'input_image_mask', 'moderation', 'output_compression',
               'output_format', 'partial_images', 'quality', 'size', 'complexity'}
MAX_RESPONSE_BYTES = 256 * 1024 * 1024
MAX_IMAGE_URL = 20971520


def require(condition, message):
    if not condition:
        raise ValueError(message)


def http_url(value):
    require(isinstance(value, str) and value and not any(c.isspace() for c in value),
            'Expected a nonempty HTTP(S) URL without whitespace')
    parsed = urllib.parse.urlsplit(value)
    require(parsed.scheme in ('http', 'https') and parsed.hostname
            and parsed.username is None and parsed.password is None,
            'Expected an HTTP(S) URL without embedded credentials')
    parsed.port  # Validate malformed port numbers before sending credentials.
    return parsed


def api_base():
    value = os.environ.get(BASE_ENV, DEFAULT_BASE).strip().rstrip('/')
    parsed = http_url(value)
    require(not parsed.query and not parsed.fragment,
            BASE_ENV + ' must not contain a query or fragment')
    return value


def api_key():
    value = os.environ.get(KEY_ENV, '').strip()
    require(value and not any(c.isspace() for c in value),
            'Set ' + KEY_ENV + ' in the execution environment')
    return value


def sanitized(value):
    text = str(value)
    key = os.environ.get(KEY_ENV, '').strip()
    return text.replace(key, '[REDACTED]') if key else text


def provider_profile(base):
    url = http_url(base)
    if (url.scheme == 'https' and url.hostname == 'api.openai.com'
            and url.port in (None, 443) and url.path == '/v1'):
        return 'openai'
    return 'compatible'


def known_family(model, provider):
    if provider != 'openai':
        return None
    for family in FAMILIES:
        if model == family or re.fullmatch(re.escape(family) + r'-\d{4}-\d{2}-\d{2}', model):
            return family
    return None


def validate_stream(body):
    require(type(body.get('stream', False)) is bool, 'stream must be a boolean')
    partial = body.get('partial_images', 0)
    require(type(partial) is int and 0 <= partial <= 3, 'partial_images must be an integer from 0 to 3')
    require(not partial or body.get('stream', False), 'partial_images requires stream=true')


def validate_fidelity(body, provider):
    if 'input_fidelity' in body:
        require(body['input_fidelity'] in ('low', 'high'), 'Invalid input_fidelity')
        family = known_family(body['model'], provider)
        require(not family or family == 'gpt-image-1.5',
                'Omit input_fidelity for GPT Image 2/2.5/2.6; this is not a configurable fidelity tier')


def validate(body, provider, editing=False):
    require(isinstance(body, dict), 'Request must be a JSON object')
    require(set(body) <= FIELDS | (EDIT_FIELDS if editing else set()),
            'Request contains unsupported fields; see references/api.md')
    require(isinstance(body.get('model'), str) and body['model'].strip(),
            'An explicit provider model ID is required')
    prompt = body.get('prompt')
    require(isinstance(prompt, str) and prompt.strip() and len(prompt) <= 32000,
            'prompt must contain 1–32000 characters')
    body = dict(body)
    family = known_family(body['model'], provider)
    if provider == 'openai':
        body.setdefault('n', 1)
        body.setdefault('output_format', 'png')
    n = body.get('n', 1)
    require(type(n) is int and 1 <= n <= 10, 'n must be an integer from 1 to 10')
    fmt = body.get('output_format', 'png')
    require(fmt in ('png', 'jpeg', 'webp', 'svg', 'gif'), 'Invalid output_format')
    if family:
        require(fmt in PROFILES[family]['output_formats'], 'Unsupported output format for the known model family')
    if 'complexity' in body:
        require(body['complexity'] in ('low', 'medium', 'high'), 'Invalid complexity')
        require(not family or family in FAMILIES_26, 'complexity requires GPT Image 2.6')
    if fmt in ('svg', 'gif'):
        require(not editing, 'SVG/GIF output is supported only by Images generation, not edits')
        require(not body.get('stream') and not body.get('partial_images'), 'SVG/GIF output cannot stream or return partial images')
        require('output_compression' not in body, 'SVG/GIF output does not support output_compression')
    if fmt == 'svg':
        require(n == 1, 'SVG output requires n=1')
    if 'svg' in body:
        svg = body['svg']
        require(fmt == 'svg' and isinstance(svg, dict) and set(svg) <= {'model', 'reasoning'},
                'svg options require output_format=svg and only model/reasoning fields')
        require(isinstance(svg.get('model'), str) and svg['model'].strip(), 'svg.model is required when selecting an SVG author')
        require(known_family(svg['model'], provider) is None, 'svg.model must be an SVG author, not a GPT Image model')
        reasoning = svg.get('reasoning')
        if reasoning is not None:
            require(isinstance(reasoning, dict) and set(reasoning) <= {'effort'}, 'Invalid SVG reasoning object')
            require(reasoning.get('effort') in (None, 'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'),
                    'Invalid SVG reasoning effort; also verify the author model supports it')
    if 'frame_count' in body:
        require(fmt == 'gif' and type(body['frame_count']) is int and 2 <= body['frame_count'] <= 16,
                'frame_count requires GIF output and an integer from 2 to 16 (conservative API reference limit)')
    if 'frame_duration_ms' in body:
        require(fmt == 'gif' and type(body['frame_duration_ms']) is int and 20 <= body['frame_duration_ms'] <= 2000,
                'frame_duration_ms requires GIF output and an integer from 20 to 2000')
    require(body.get('background', 'auto') in ('auto', 'opaque', 'transparent'), 'Invalid background')
    require(body.get('background') != 'transparent' or fmt in ('png', 'webp'),
            'Transparent backgrounds require PNG or WebP')
    if 'output_compression' in body:
        require(type(body['output_compression']) is int and 0 <= body['output_compression'] <= 100
                and fmt in ('jpeg', 'webp'),
                'output_compression requires JPEG/WebP and an integer from 0 to 100')
    require(body.get('moderation', 'auto') in ('auto', 'low'), 'Invalid moderation')
    if 'safety_identifier' in body:
        value = body['safety_identifier']
        require(isinstance(value, str) and value.strip() and len(value) <= 128,
                'safety_identifier must contain 1–128 characters')
    if 'user' in body:
        require(isinstance(body['user'], str), 'user must be a string; prefer safety_identifier')
    validate_stream(body)
    if editing:
        validate_fidelity(body, provider)
        require(isinstance(body.get('images'), list) and 1 <= len(body['images']) <= 16,
                'Edit requires 1–16 images')
        require(not ('mask' in body and 'markup' in body), 'mask and markup cannot be combined')
        if 'markup' in body:
            require(not family or PROFILES[family]['markup'], 'markup requires GPT Image 2.5/2.6')
    quality = body.get('quality', 'auto')
    require(isinstance(quality, str) and quality.strip(), 'quality must be a nonempty string')
    if family:
        require(quality in PROFILES[family]['quality'], 'Unsupported quality for the known model family')
    size = body.get('size', 'auto')
    require(isinstance(size, str), 'size must be auto or WIDTHxHEIGHT')
    if size != 'auto':
        match = re.fullmatch(r'([1-9]\d{0,5})x([1-9]\d{0,5})', size)
        require(match is not None, 'size must be auto or WIDTHxHEIGHT')
        width, height = map(int, match.groups())
        if family == 'gpt-image-1.5':
            require(size in ('1024x1024', '1536x1024', '1024x1536'),
                    'Unsupported size for gpt-image-1.5')
        elif family in FAMILIES_26 or fmt == 'gif':
            require(width % 16 == 0 and height % 16 == 0, 'Dimensions must be multiples of 16')
            # Do not copy 2/2.5 raster pixel limits to 2.6 or animated frames.
            # Provider-specific edge and total animation budgets still need verification.
        elif family:
            require(width % 16 == 0 and height % 16 == 0
                    and width <= 3 * height and height <= 3 * width,
                    'Known GPT Image 2/2.5 sizes need multiples of 16 and aspect ratio 1:3–3:1')
            require(max(width, height) <= 3840 and 655360 <= width * height <= 8294400,
                    'GPT Image 2/2.5 size exceeds its pixel or edge limits')
    return body


def png_info(data):
    require(len(data) >= 33 and data[12:16] == b'IHDR', 'Invalid PNG header')
    width, height = int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    require(width > 0 and height > 0, 'Invalid PNG dimensions')
    alpha = data[25] in (4, 6)
    offset = 8
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], 'big')
        kind = data[offset + 4:offset + 8]
        if kind == b'tRNS':
            alpha = True
        offset += length + 12
        if kind == b'IEND':
            break
    return width, height, alpha


def png_transparency(data):
    """Validate/decode a PNG and find nonopaque pixels, including Adam7 passes.

    Only local/data markup needs this check. Limit total inflated scanlines to
    64 MiB before decompressing; remote/file references stay provider validated.
    """
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid markup PNG signature')
    view = memoryview(data)
    offset, count = 8, 0
    header, palette, transparency = None, None, None
    compressed = []
    image_started, image_ended, ended = False, False, False
    while offset < len(data):
        count += 1
        require(count <= 100000 and offset + 12 <= len(data), 'Invalid or excessive PNG chunks')
        length = int.from_bytes(view[offset:offset + 4], 'big')
        kind = bytes(view[offset + 4:offset + 8])
        end = offset + 12 + length
        require(length < 2 ** 31 and end <= len(data), 'Truncated markup PNG chunk')
        payload = view[offset + 8:end - 4]
        checksum = binascii.crc32(payload, binascii.crc32(kind)) & 0xffffffff
        require(checksum == int.from_bytes(view[end - 4:end], 'big'), 'Invalid markup PNG CRC')
        require(len(kind) == 4 and all(65 <= byte <= 90 or 97 <= byte <= 122 for byte in kind),
                'Invalid PNG chunk type')
        require(header is not None or kind == b'IHDR', 'PNG must begin with IHDR')
        if kind == b'IHDR':
            require(header is None and length == 13, 'Invalid or duplicate PNG IHDR')
            header = bytes(payload)
        elif kind == b'PLTE':
            require(palette is None and not image_started and transparency is None
                    and 0 < length <= 768 and length % 3 == 0, 'Invalid PNG palette')
            palette = bytes(payload)
        elif kind == b'tRNS':
            require(transparency is None and not image_started, 'Invalid PNG transparency chunk')
            transparency = bytes(payload)
        elif kind == b'IDAT':
            require(not image_ended, 'PNG IDAT chunks must be consecutive')
            compressed.append(payload)
            image_started = True
        elif kind == b'IEND':
            require(length == 0 and image_started and end == len(data), 'Invalid PNG end')
            ended = True
            break
        else:
            require(kind[0] & 32, 'Unsupported critical markup PNG chunk')
            require(kind not in (b'acTL', b'fcTL', b'fdAT'), 'Animated PNG markup is unsupported')
        if image_started and kind != b'IDAT':
            image_ended = True
        offset = end
    require(ended and header is not None, 'Incomplete markup PNG')
    width, height = int.from_bytes(header[:4], 'big'), int.from_bytes(header[4:8], 'big')
    depth, color, compression, filtering, interlace = header[8:]
    allowed = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
    require(0 < width < 2 ** 31 and 0 < height < 2 ** 31 and color in allowed
            and depth in allowed[color] and compression == filtering == 0 and interlace in (0, 1),
            'Unsupported or invalid markup PNG encoding')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    maximum = (1 << depth) - 1
    if color == 3:
        require(palette is not None and len(palette) // 3 <= 1 << depth, 'Missing or invalid PNG palette')
    elif color in (0, 4):
        require(palette is None, 'Grayscale PNG cannot have a palette')
    if transparency is not None:
        require(color in (0, 2, 3), 'PNG alpha types cannot contain tRNS')
        if color == 3:
            require(0 < len(transparency) <= len(palette) // 3, 'Invalid PNG palette transparency')
        else:
            require(len(transparency) == channels * 2 and all(
                int.from_bytes(transparency[index:index + 2], 'big') <= maximum
                for index in range(0, len(transparency), 2)), 'Invalid PNG transparent sample')
    passes = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
              (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)) if interlace else ((0, 0, 1, 1),)
    rows, expected = [], 0
    for start_x, start_y, step_x, step_y in passes:
        pass_width = max(0, (width - start_x + step_x - 1) // step_x)
        pass_height = max(0, (height - start_y + step_y - 1) // step_y)
        if pass_width and pass_height:
            row_bytes = (pass_width * channels * depth + 7) // 8
            rows.append((pass_width, pass_height, row_bytes))
            expected += pass_height * (1 + row_bytes)
    require(expected <= 64 * 1024 * 1024, 'Markup PNG decoding exceeds the 64 MiB scanline limit')
    # max_length prevents a forged header or a DEFLATE bomb from allocating unbounded data.
    decoder = zlib.decompressobj()
    inflated = bytearray()
    try:
        for part in compressed:
            inflated.extend(decoder.decompress(part, expected + 1 - len(inflated)))
            require(len(inflated) <= expected and not decoder.unconsumed_tail
                    and not decoder.unused_data, 'Markup PNG exceeds its declared pixel data')
        require(decoder.eof and len(inflated) == expected, 'Incomplete markup PNG pixel data')
    except zlib.error:
        raise ValueError('Invalid compressed markup PNG data') from None
    offset, transparent = 0, False
    stride = max(1, (channels * depth + 7) // 8)
    transparent_sample = (int.from_bytes(transparency, 'big')
                          if color == 0 and transparency is not None else None)
    transparent_rgb = None
    if color == 2 and transparency is not None:
        transparent_rgb = transparency if depth == 16 else transparency[1::2]
    for pass_width, pass_height, row_bytes in rows:
        previous = bytearray(row_bytes)
        for _ in range(pass_height):
            filter_type = inflated[offset]
            require(filter_type <= 4, 'Invalid markup PNG row filter')
            row = bytearray(inflated[offset + 1:offset + 1 + row_bytes])
            offset += row_bytes + 1
            if filter_type:
                for index in range(row_bytes):
                    left = row[index - stride] if index >= stride else 0
                    up = previous[index]
                    upper_left = previous[index - stride] if index >= stride else 0
                    if filter_type == 1:
                        predictor = left
                    elif filter_type == 2:
                        predictor = up
                    elif filter_type == 3:
                        predictor = (left + up) // 2
                    else:
                        estimate = left + up - upper_left
                        distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
                        predictor = (left if distances[0] <= min(distances[1:]) else
                                     up if distances[1] <= distances[2] else upper_left)
                    row[index] = (row[index] + predictor) & 255
            if color in (4, 6):
                alpha_offset = (channels - 1) * (depth // 8)
                transparent |= any(value != 255 for value in row[alpha_offset::stride])
                if depth == 16:
                    transparent |= any(value != 255 for value in row[alpha_offset + 1::stride])
            elif color == 2 and transparent_rgb is not None:
                transparent |= any(row[index:index + stride] == transparent_rgb
                                   for index in range(0, row_bytes, stride))
            elif color in (0, 3):
                for index in range(pass_width):
                    bit = index * depth
                    if depth < 8:
                        sample = row[bit // 8] >> (8 - depth - bit % 8) & maximum
                    else:
                        start = index * (depth // 8)
                        sample = int.from_bytes(row[start:start + depth // 8], 'big')
                    if color == 3:
                        require(sample < len(palette) // 3, 'PNG pixel has an invalid palette index')
                        transparent |= (transparency is not None and sample < len(transparency)
                                        and transparency[sample] != 255)
                    else:
                        transparent |= sample == transparent_sample
            previous = row
    return transparent


def image_ref(ref, root, overlay=False, json_limit=True):
    require(isinstance(ref, dict) and len(ref) == 1 and
            set(ref) <= {'path', 'image_url', 'file_id'},
            'Image reference requires exactly one of path, image_url, or file_id')
    field, value = next(iter(ref.items()))
    require(isinstance(value, str) and value.strip(), 'Image reference must be nonempty')
    data = None
    if field == 'path':
        path = (root / Path(value).expanduser()).resolve()
        require(path.is_file() and path.stat().st_size < 50 * 1024 * 1024,
                'Local image must be a file smaller than 50 MiB')
        data = path.read_bytes()
        fmt = image_format(data)
        value = 'data:image/{};base64,{}'.format(fmt, base64.b64encode(data).decode('ascii'))
        field = 'image_url'
    if field == 'image_url':
        require(not json_limit or len(value) <= MAX_IMAGE_URL,
                'image_url exceeds 20,971,520 characters; use a file_id, HTTPS URL, or multipart for synchronous edits')
        if value.startswith('data:'):
            match = re.fullmatch(r'data:image/(png|jpeg|webp);base64,(.+)', value, re.DOTALL)
            require(match is not None, 'Use a PNG, JPEG, or WebP base64 data URL')
            try:
                data = base64.b64decode(match.group(2), validate=True)
            except (ValueError, binascii.Error):
                raise ValueError('Invalid input image base64') from None
            require(len(data) < 50 * 1024 * 1024 and image_format(data) == match.group(1),
                    'Input image encoding does not match its MIME type or exceeds 50 MiB')
        else:
            require(http_url(value).scheme == 'https', 'Input image URLs must use HTTPS')
    if data is not None and overlay:
        require(image_format(data) == 'png', 'mask/markup must be PNG with an alpha channel')
        require(png_info(data)[2], 'mask/markup requires an alpha channel or PNG transparency')
        if overlay == 'markup':
            require(png_transparency(data), 'markup requires actual transparent pixels')
    return {field: value}, png_info(data)[:2] if data is not None and image_format(data) == 'png' else None


def prepare_edit(body, root, provider, transport='json'):
    body = validate(body, provider, editing=True)
    refs = [image_ref(ref, root, json_limit=transport != 'multipart') for ref in body['images']]
    body['images'] = [ref for ref, _ in refs]
    first_url = body['images'][0].get('image_url', '')
    require('mask' not in body or not first_url.startswith('data:') or first_url.startswith('data:image/png;'),
            'A local/data source and mask must have matching formats; use PNG for both')
    for field in ('mask', 'markup'):
        if field in body:
            body[field], dimensions = image_ref(body[field], root, overlay=field, json_limit=transport != 'multipart')
            require(not dimensions or not refs[0][1] or dimensions == refs[0][1],
                    'mask/markup dimensions must match the first input image')
    return body


def edit_transport(body, requested, provider):
    body = validate(body, provider, editing=True)
    refs = body['images'] + [body[field] for field in ('mask', 'markup') if field in body]
    inline = all(isinstance(ref, dict) and len(ref) == 1 and
                 ('path' in ref or isinstance(ref.get('image_url'), str)
                  and ref['image_url'].startswith('data:')) for ref in refs)
    if requested == 'auto':
        return 'multipart' if inline else 'json'
    require(requested != 'multipart' or inline,
            'Multipart requires local paths or data URLs for every reference; use JSON for HTTPS URLs/file_id. No remote download or upload is automatic')
    return requested


def multipart_edit(body, image_field=None):
    boundary = 'imagegen-' + uuid.uuid4().hex
    parts = []
    def part(name, data, filename=None, mime=None):
        disposition = 'Content-Disposition: form-data; name="' + name + '"'
        if filename:
            disposition += '; filename="' + filename + '"'
        headers = [('--' + boundary).encode('ascii'), disposition.encode('ascii')]
        if mime:
            headers.append(('Content-Type: ' + mime).encode('ascii'))
        parts.append(b'\r\n'.join(headers) + b'\r\n\r\n' + data + b'\r\n')
    for key, value in body.items():
        if key not in EDIT_FIELDS:
            part(key, (value if isinstance(value, str) else json.dumps(value, allow_nan=False)).encode('utf-8'))
        elif key == 'input_fidelity':
            part(key, value.encode('utf-8'))
    for field in ('images', 'mask', 'markup'):
        if field not in body:
            continue
        refs = body[field] if field == 'images' else [body[field]]
        name = (image_field or ('image' if len(refs) == 1 else 'image[]')) if field == 'images' else field
        for index, ref in enumerate(refs, 1):
            url = ref.get('image_url', '')
            require(url.startswith('data:image/'), 'Multipart requires inline image bytes')
            data = base64.b64decode(url.split(',', 1)[1], validate=True)
            fmt = image_format(data)
            part(name, data, '{}-{}.{}'.format(field, index, fmt), 'image/' + fmt)
    parts.append(('--' + boundary + '--\r\n').encode('ascii'))
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


def prepare_responses(body, root, provider):
    require(isinstance(body, dict), 'Request must be a JSON object')
    body = dict(body)
    require(isinstance(body.get('model'), str) and body['model'].strip(), 'An explicit mainline model is required')
    require(known_family(body['model'], provider) is None,
            'Responses top-level model must be a mainline model, not GPT Image')
    require('input' in body and isinstance(body['input'], (str, list)) and body['input'],
            'Responses requires a nonempty input string or array')
    tools = body.get('tools')
    require(isinstance(tools, list) and len(tools) == 1 and isinstance(tools[0], dict)
            and tools[0].get('type') == 'image_generation', 'Use exactly one image_generation tool')
    tool = dict(tools[0])
    require(set(tool) <= TOOL_FIELDS, 'Unsupported image_generation tool field; see references/api.md')
    require(isinstance(tool.get('model'), str) and tool['model'].strip(), 'An explicit image tool model is required')
    require(tool.get('output_format', 'png') in ('png', 'jpeg', 'webp'),
            'Responses image tools support raster PNG/JPEG/WebP output only in this helper')
    # Reuse image option checks without sending synthetic generation parameters.
    options = {key: value for key, value in tool.items() if key in FIELDS}
    options.update(prompt='Validate image tool settings', stream=body.get('stream', False))
    validate(options, provider)
    validate_fidelity(tool, provider)
    require(tool.get('action', 'auto') in ('auto', 'generate', 'edit'), 'Invalid image tool action')
    if 'input_image_mask' in tool:
        tool['input_image_mask'], _ = image_ref(tool['input_image_mask'], root, overlay=True)
    body['tools'] = [tool]
    if provider == 'openai':
        body.setdefault('tool_choice', {'type': 'image_generation'})
    require(body.get('background', False) is False, 'Background Responses jobs are not supported; use Batch')
    for field in ('previous_response_id', 'safety_identifier'):
        if field in body:
            require(isinstance(body[field], str) and body[field].strip(), field + ' must be nonempty')
    if 'safety_identifier' in body:
        require(len(body['safety_identifier']) <= 128, 'safety_identifier is too long')
    if isinstance(body['input'], list):
        prepared = []
        for item in body['input']:
            require(isinstance(item, dict), 'Responses input items must be objects')
            item = dict(item)
            if isinstance(item.get('content'), list):
                content = []
                for part in item['content']:
                    require(isinstance(part, dict), 'Responses content must contain objects')
                    part = dict(part)
                    if part.get('type') == 'input_image':
                        keys = set(part) & {'path', 'image_url', 'file_id'}
                        ref, _ = image_ref({key: part[key] for key in keys}, root)
                        part = {key: value for key, value in part.items() if key not in keys}
                        part.update(ref)
                    content.append(part)
                item['content'] = content
            prepared.append(item)
        body['input'] = prepared
    has_context = bool(body.get('previous_response_id'))
    for item in body['input'] if isinstance(body['input'], list) else []:
        if item.get('type') in ('image_generation_call', 'item_reference'):
            has_context = True
        content = item.get('content')
        if isinstance(content, list):
            has_context = has_context or any(part.get('type') == 'input_image' for part in content)
    require(tool.get('action') != 'edit' or has_context,
            'action=edit requires an input image, earlier image call, or previous_response_id')
    require('input_image_mask' not in tool or has_context, 'input_image_mask requires image context')
    return body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def read_limited(response):
    declared = response.headers.get('Content-Length')
    if declared is not None:
        require(0 <= int(declared) <= MAX_RESPONSE_BYTES, 'Invalid or oversized response Content-Length')
    data = response.read(MAX_RESPONSE_BYTES + 1)
    require(len(data) <= MAX_RESPONSE_BYTES, 'Response exceeds the helper limit of 256 MiB')
    require(declared is None or len(data) == int(declared), 'Incomplete HTTP response; no automatic retry')
    return data


def request_json(base, key, method, path, timeout, body=None, run_dir=None, raw=None,
                 content_type='application/json', stream=False, expected=1):
    payload = raw if raw is not None else (None if body is None else
              json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    req = urllib.request.Request(base + path, data=payload, method=method, headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': content_type, 'User-Agent': USER_AGENT,
        'Accept': 'text/event-stream' if stream else 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            request_id = response.headers.get('x-request-id', '')
            if stream:
                require('text/event-stream' in response.headers.get('Content-Type', ''),
                        'Expected an SSE response for stream=true')
                write_json(run_dir / 'response-meta.json', {
                    'model': body['tools'][0]['model'] if path == '/responses' else body['model'],
                    'request_id': request_id})
                result = read_stream(response, run_dir, path, expected)
            else:
                result = json.loads(read_limited(response))
    except urllib.error.HTTPError as exc:
        request_id = exc.headers.get('x-request-id', '')
        try:
            error = json.loads(exc.read(65536)).get('error', {})
            detail = error.get('message', '') if isinstance(error, dict) else str(error)
            code = error.get('code', '') if isinstance(error, dict) else ''
        except (ValueError, AttributeError):
            detail, code = 'Non-JSON error response', ''
        raise RuntimeError(sanitized('API HTTP {}; code={}; {}; request_id={}'.format(
            exc.code, code, detail, request_id))[:2000]) from None
    require(isinstance(result, dict), 'API must return a JSON object')
    require(not result.get('error'), 'API returned an error object; no automatic retry')
    return result, request_id


def sse_events(response):
    data, event_name, total = [], '', 0
    declared = response.headers.get('Content-Length')
    if declared is not None:
        require(0 <= int(declared) <= MAX_RESPONSE_BYTES, 'Invalid or oversized stream Content-Length')
    while True:
        line = response.readline(MAX_RESPONSE_BYTES + 1)
        total += len(line)
        require(total <= MAX_RESPONSE_BYTES, 'Stream exceeds the helper limit of 256 MiB')
        if not line:
            require(not data, 'Stream ended in an incomplete SSE event')
            break
        line = line.decode('utf-8').rstrip('\r\n')
        if not line:
            if data:
                payload = '\n'.join(data)
                if payload == '[DONE]':
                    break
                event = json.loads(payload)
                require(isinstance(event, dict), 'SSE data must be a JSON object')
                event.setdefault('type', event_name)
                yield event
            data, event_name = [], ''
        elif line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
        elif line.startswith('event:'):
            event_name = line[6:].lstrip(' ')
    require(declared is None or total == int(declared), 'Incomplete HTTP stream response; no automatic retry')


def read_stream(response, run_dir, path, expected):
    final, images, metadata, completed_calls = None, [], {}, []
    response_id, mainline_model = None, None
    prefix = 'image_edit' if path == '/images/edits' else 'image_generation'
    with (run_dir / 'events.jsonl').open('x', encoding='utf-8') as log:
        for event in sse_events(response):
            log.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
            log.flush()
            kind = event.get('type', '')
            if path == '/responses' and isinstance(event.get('response'), dict):
                response_id = event['response'].get('id', response_id)
                mainline_model = event['response'].get('model', mainline_model)
            if kind in ('error', 'response.failed', 'response.incomplete') or event.get('error'):
                raise RuntimeError('Stream failed: ' + sanitized(json.dumps(event, ensure_ascii=False))[:1500])
            if kind in (prefix + '.partial_image', 'response.image_generation_call.partial_image'):
                encoded = event.get('partial_image_b64') if kind.startswith('response.') else event.get('b64_json')
                content = image_bytes({'b64_json': encoded}, 1)
                fmt = image_format(content)
                # Number locally: provider call IDs/indices never become filesystem paths.
                count = len(list(run_dir.glob('partial-*'))) + 1
                preview = run_dir / ('partial-{:03d}.{}'.format(count, fmt))
                with preview.open('xb') as handle:
                    handle.write(content)
                print(json.dumps({'stage': 'partial_image', 'path': str(preview),
                                  'partial_image_index': event.get('partial_image_index')}),
                      file=sys.stderr, flush=True)
            elif kind == prefix + '.completed':
                require(isinstance(event.get('b64_json'), str) and event['b64_json'],
                        'Completed image event has no image')
                images.append({'b64_json': event['b64_json']})
                metadata.update({key: event[key] for key in
                                 ('created', 'size', 'quality', 'background', 'output_format', 'usage') if key in event})
                # Persist each completed image before reading any later events.
                final = dict(metadata, data=list(images))
                write_json_replace(run_dir / 'response.json', final)
            elif kind == 'response.output_item.done' and path == '/responses':
                item = event.get('item')
                if (isinstance(item, dict) and item.get('type') == 'image_generation_call'
                        and item.get('status') == 'completed' and item.get('result') and not item.get('error')):
                    completed_calls.append(item)
                    # These final image bytes can be recovered even if the response later disconnects.
                    write_json_replace(run_dir / 'response.json', {
                        'id': response_id, 'model': mainline_model, 'status': 'incomplete',
                        'output': list(completed_calls)})
            elif kind == 'response.completed':
                require(final is None, 'Duplicate response.completed event')
                final = event.get('response')
                require(isinstance(final, dict), 'Missing completed Responses payload')
                write_json_replace(run_dir / 'response.json', final)
    require(final is not None, 'Stream ended without a final image response; keep events.jsonl; no automatic retry')
    if path != '/responses' and expected is not None:
        require(len(images) == expected, 'Stream ended with {} of {} final images; recover saved response; no automatic retry'.format(
            len(images), expected))
    return final


def write_json_replace(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
    temporary.replace(path)


def list_models(base, key, timeout):
    rows, seen_ids, cursors = [], set(), set()
    path = '/models'
    for _ in range(100):
        result, _ = request_json(base, key, 'GET', path, timeout)
        page = result.get('data')
        require(isinstance(page, list), 'Model response must contain a data array')
        for row in page:
            require(isinstance(row, dict) and isinstance(row.get('id'), str) and row['id'].strip(),
                    'Model response contains an invalid model ID')
            if row['id'] not in seen_ids:
                rows.append(row)
                seen_ids.add(row['id'])
        if not result.get('has_more'):
            return rows
        cursor = result.get('last_id') or (page[-1]['id'] if page else None)
        require(isinstance(cursor, str) and cursor and cursor not in cursors,
                'Model pagination did not advance; refusing an incomplete catalog')
        cursors.add(cursor)
        path = '/models?' + urllib.parse.urlencode({'after': cursor})
    raise ValueError('Model pagination exceeded 100 pages; refusing an incomplete catalog')


def model_selection(provider, model_ids, skip_discovery):
    require(not skip_discovery or provider == 'compatible',
            '--skip-model-discovery is only available with a compatible provider')
    return {'provider_profile': provider, 'required_model_ids': sorted(model_ids),
            'catalog_check': 'skipped' if skip_discovery else 'pending'}


def verify_model_selection(base, key, timeout, selection):
    if selection['catalog_check'] == 'skipped':
        return
    catalog = list_models(base, key, min(timeout, 30))
    missing = set(selection['required_model_ids']) - {row['id'] for row in catalog}
    require(not missing, 'Selected model IDs absent from the fresh provider catalog; no submission: '
            + ', '.join(sorted(missing)))
    selection['catalog_check'] = 'verified'


def new_run(output_dir):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = 'imagegen-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-')
    if os.name != 'nt':
        return Path(tempfile.mkdtemp(prefix=prefix, dir=str(output_dir)))

    # Windows run artifacts should inherit the chosen output directory's ACL.
    while True:
        run_dir = output_dir / (prefix + uuid.uuid4().hex)
        try:
            run_dir.mkdir()
        except FileExistsError:
            continue
        return run_dir


def write_json(path, data):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def response_image_model(response):
    if isinstance(response.get('output'), list):
        tools = response.get('tools') or []
        models = {tool['model'] for tool in tools if isinstance(tool, dict)
                  and tool.get('type') == 'image_generation' and isinstance(tool.get('model'), str)}
        return next(iter(models)) if len(models) == 1 else None
    return response.get('model')


def store_response(response, run_dir, model=None, request_id=''):
    write_json_replace(run_dir / 'response-meta.json', {'model': model or response_image_model(response),
                                                      'request_id': request_id})
    write_json_replace(run_dir / 'response.json', response)


def image_format(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    raise ValueError('Returned data is not a recognized PNG, JPEG, or WebP image')


def image_bytes(item, timeout):
    require(isinstance(item, dict), 'Each response image must be an object')
    encoded = item.get('b64_json')
    if isinstance(encoded, str) and encoded:
        try:
            return base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError('Invalid image base64 in response') from None
    url = item.get('url')
    http_url(url)
    # Keep redirects disabled, including for downloads, to reject unvalidated URL schemes.
    # These requests deliberately have no Authorization header.
    with urllib.request.build_opener(NoRedirect()).open(
            urllib.request.Request(url, headers={'Accept': 'image/*'}), timeout=timeout) as response:
        return read_limited(response)


def output_image_format(data):
    # Output-only formats must not become accepted edit/upload inputs.
    if len(data) >= 13 and data[:6] in (b'GIF87a', b'GIF89a'):
        require(int.from_bytes(data[6:8], 'little') > 0 and int.from_bytes(data[8:10], 'little') > 0,
                'Invalid GIF dimensions')
        return 'gif'
    if data.lstrip().startswith((b'<', b'\xef\xbb\xbf')):
        try:
            xml = data.decode('utf-8-sig')
            require('<!DOCTYPE' not in xml.upper() and '<!ENTITY' not in xml.upper(),
                    'SVG output must not contain DTDs or entity declarations')
            root = ET.fromstring(xml)
        except (UnicodeError, ET.ParseError):
            raise ValueError('Invalid UTF-8 SVG output') from None
        require(root.tag in ('svg', '{http://www.w3.org/2000/svg}svg'), 'Returned XML is not SVG')
        return 'svg'
    return image_format(data)


def save_images(response, run_dir, timeout, model=None, request_id=''):
    data = response.get('data')
    calls, failed_calls = [], []
    response_complete = True
    if isinstance(response.get('output'), list):
        for item in response['output']:
            if not isinstance(item, dict) or item.get('type') != 'image_generation_call':
                continue
            if item.get('status', 'completed') == 'completed' and item.get('result') and not item.get('error'):
                calls.append(item)
            else:
                failed_calls.append({key: item[key] for key in ('id', 'status', 'error') if key in item})
        response_complete = response.get('status', 'completed') == 'completed' and not response.get('error') and not failed_calls
        data = [{'b64_json': item['result']} for item in calls]
    require(isinstance(data, list) and data, 'Response contains no images; do not automatically regenerate')
    manifest = {'model': model or response_image_model(response), 'request_id': request_id,
                'run_dir': str(run_dir), 'response_file': str(run_dir / 'response.json'), 'images': []}
    manifest['metadata'] = {key: response[key] for key in
                            ('created', 'size', 'quality', 'complexity', 'background', 'output_format',
                             'frame_count', 'frame_duration_ms', 'usage', 'svg_usage') if key in response}
    if calls:
        manifest['response_id'] = response.get('id')
        manifest['mainline_model'] = response.get('model')
        manifest['response_status'] = response.get('status')
        manifest['complete'] = response_complete
        manifest['failed_image_generation_calls'] = failed_calls
        manifest['image_generation_calls'] = [{key: item[key] for key in
            ('id', 'status', 'revised_prompt', 'size', 'quality', 'background', 'output_format', 'action')
            if key in item} for item in calls]
    for index, item in enumerate(data, 1):
        content = image_bytes(item, timeout)
        fmt = output_image_format(content)
        path = run_dir / ('image-{:02d}.{}'.format(index, fmt))
        with path.open('xb') as handle:
            handle.write(content)
        manifest['images'].append({'path': str(path), 'format': fmt, 'bytes': len(content)})
    manifest['partial_images'] = [str(path) for path in sorted(run_dir.glob('partial-*'))]
    write_json(run_dir / 'manifest.json', manifest)
    return manifest


def load_json(path):
    def reject_constant(value):
        raise ValueError('Non-finite numbers are not valid JSON')
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_constant)


def safe_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]+', value), 'Invalid API object ID')
    return value


def upload_file(base, key, data, filename, purpose, timeout):
    boundary = 'imagegen-' + uuid.uuid4().hex
    crlf = bytes((13, 10))
    # filename is always helper generated, never an untrusted local path.
    multipart = crlf.join([
        ('--' + boundary).encode('ascii'),
        b'Content-Disposition: form-data; name="purpose"', b'', purpose.encode('ascii'),
        ('--' + boundary).encode('ascii'),
        ('Content-Disposition: form-data; name="file"; filename="' + filename + '"').encode('ascii'),
        b'Content-Type: application/octet-stream', b'', data,
        ('--' + boundary + '--').encode('ascii'), b''])
    return request_json(base, key, 'POST', '/files', timeout, raw=multipart,
                        content_type='multipart/form-data; boundary=' + boundary)


def batch_input_lines(path):
    # JSON strings may contain U+0085/U+2028; only LF separates JSONL records.
    with path.open('r', encoding='utf-8', newline='\n') as handle:
        yield from handle


def download_batch_file(base, key, file_id, saved, timeout, chunk_size=1024 * 1024):
    file_id = safe_id(file_id)
    partial = saved.with_suffix(saved.suffix + '.partial')
    record = {'file_id': file_id, 'path': str(partial),
              'bytes_downloaded': 0, 'complete': False}
    try:
        req = urllib.request.Request(base + '/files/' + file_id + '/content',
                                     headers={'Authorization': 'Bearer ' + key, 'User-Agent': USER_AGENT})
        with partial.open('xb') as handle:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
                declared = response.headers.get('Content-Length')
                if declared is not None:
                    declared = int(declared)
                    require(declared >= 0, 'Invalid batch Content-Length')
                    record['expected_bytes'] = declared
                while True:
                    try:
                        chunk = response.read(chunk_size)
                    except http.client.IncompleteRead as exc:
                        handle.write(exc.partial)
                        record['bytes_downloaded'] += len(exc.partial)
                        raise
                    if not chunk:
                        break
                    handle.write(chunk)
                    record['bytes_downloaded'] += len(chunk)
                require(declared is None or record['bytes_downloaded'] == declared,
                        'Incomplete batch HTTP response')
        partial.replace(saved)
        record.update(path=str(saved), complete=True)
    except (ValueError, OSError, http.client.HTTPException) as exc:
        # Keep bytes supplied by IncompleteRead, and never repeat the request.
        if partial.exists():
            record['bytes_downloaded'] = partial.stat().st_size
        record['error'] = sanitized(exc) + '; no automatic retry'
    return record


def batch_result_lines(path, max_line_bytes=None):
    # Bound one JSON object, never the total file. Drain oversized lines in
    # bounded pieces so later valid records still get processed.
    limit = MAX_RESPONSE_BYTES if max_line_bytes is None else max_line_bytes
    require(limit > 0, 'Batch line limit must be positive')
    with path.open('rb') as handle:
        number = 0
        while True:
            line = handle.readline(limit + 1)
            if not line:
                break
            number += 1
            if len(line) > limit:
                while line and not line.endswith(b'\n'):
                    line = handle.readline(min(limit + 1, 65536))
                yield number, None
            else:
                yield number, line


def prepare_batch(path, provider, endpoint=None):
    require(path.stat().st_size <= 200 * 1024 * 1024, 'Batch input exceeds 200 MiB')
    rows, ids, models, routes = [], set(), set(), set()
    for number, line in enumerate(batch_input_lines(path), 1):
        require(line.strip(), 'Blank batch line at {}'.format(number))
        row = json.loads(line)
        require(isinstance(row, dict) and set(row) == {'custom_id', 'method', 'url', 'body'},
                'Batch lines require custom_id, method, url, body')
        custom_id = row['custom_id']
        require(isinstance(custom_id, str) and custom_id and custom_id not in ids,
                'Batch custom_id values must be nonempty and unique')
        require(row['method'] == 'POST', 'Batch image requests must use POST')
        route = row['url']
        require(route in ('/v1/images/generations', '/v1/images/edits', '/v1/responses'),
                'Use a supported /v1/ endpoint in batch rows')
        if route == '/v1/images/edits':
            body = prepare_edit(row['body'], path.resolve().parent, provider)
        elif route == '/v1/responses':
            body = prepare_responses(row['body'], path.resolve().parent, provider)
        else:
            body = validate(row['body'], provider)
        require(not body.get('stream'), 'Batch requests cannot stream')
        image_model = body['tools'][0]['model'] if route == '/v1/responses' else body['model']
        if route != '/v1/responses':
            family = known_family(image_model, provider)
            require(not family or PROFILES[family]['image_batch_documented'],
                    'OpenAI Batch on the Images endpoints is documented here only for GPT Image 2.5')
        rows.append(dict(row, body=body))
        ids.add(custom_id)
        author = (body['svg']['model'],) if route == '/v1/images/generations' and 'svg' in body else ()
        models.add((body['model'], image_model) + author)
        routes.add(route)
        require(len(rows) <= 50000, 'Batch exceeds 50,000 requests')
    require(rows and len(routes) == 1 and len(models) == 1, 'A batch requires one endpoint and one model configuration')
    route = next(iter(routes))
    if endpoint:
        require(route == ('/v1' + endpoint if not endpoint.startswith('/v1/') else endpoint),
                '--endpoint must match batch row URLs')
    payload = ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + chr(10) for row in rows).encode('utf-8')
    require(len(payload) <= 200 * 1024 * 1024, 'Expanded batch input exceeds 200 MiB')
    return rows, payload, route, set(next(iter(models)))


def run_batch(args):
    if args.command == 'batch-submit':
        base = api_base()
        provider = provider_profile(base)
        rows, payload, endpoint, required_models = prepare_batch(args.jsonl, provider, args.endpoint)
        selection = model_selection(provider, required_models, args.skip_model_discovery)
        if args.dry_run:
            return {'dry_run': True, 'requests': len(rows), 'endpoint': endpoint,
                    'models': sorted(required_models), 'bytes': len(payload), 'model_availability_checked': False,
                    'model_selection': selection}
        key = api_key()
        verify_model_selection(base, key, args.timeout, selection)
        run_dir = new_run(args.output_dir)
        (run_dir / 'input.jsonl').write_bytes(payload)
        write_json(run_dir / 'request-meta.json', {'model_selection': selection})
        print(json.dumps({'stage': 'batch_upload', 'run_dir': str(run_dir)}), file=sys.stderr, flush=True)
        uploaded, _ = upload_file(base, key, payload, 'input.jsonl', 'batch', args.timeout)
        write_json(run_dir / 'uploaded-file.json', uploaded)
        file_id = safe_id(uploaded.get('id'))
        batch, request_id = request_json(base, key, 'POST', '/batches', args.timeout,
            {'input_file_id': file_id, 'endpoint': endpoint, 'completion_window': '24h'})
        write_json(run_dir / 'batch.json', batch)
        return {'run_dir': str(run_dir), 'request_id': request_id, 'batch': batch, 'model_selection': selection}
    base, key = api_base(), api_key()
    path = '/batches/' + safe_id(args.id)
    if args.command == 'batch-cancel':
        result, request_id = request_json(base, key, 'POST', path + '/cancel', args.timeout, {})
        return {'request_id': request_id, 'batch': result}
    batch, request_id = request_json(base, key, 'GET', path, args.timeout)
    if args.command == 'batch-status':
        return {'request_id': request_id, 'batch': batch}
    require(batch.get('output_file_id') or batch.get('error_file_id'),
            'Batch has no result files yet; status=' + str(batch.get('status')))
    run_dir = new_run(args.output_dir)
    write_json(run_dir / 'batch.json', batch)
    manifest = {'run_dir': str(run_dir), 'batch_id': args.id, 'status': batch.get('status'),
                'results': [], 'errors': [], 'files': [], 'downloads': []}
    for kind in ('output', 'error'):
        file_id = batch.get(kind + '_file_id')
        if not file_id:
            continue
        saved = run_dir / (kind + '.jsonl')
        download = download_batch_file(base, key, file_id, saved, args.timeout)
        manifest['downloads'].append(download)
        manifest['files'].append(download['path'])
        if not download['complete']:
            manifest['errors'].append(dict(download, custom_id=None,
                                           source_file=download['path']))
            continue
        for line_number, line in batch_result_lines(saved):
            row, child = None, None
            try:
                require(line is not None, 'Batch result line exceeds the helper limit of 256 MiB')
                row = json.loads(line.decode('utf-8'))
                require(isinstance(row, dict), 'Batch result row must be an object')
                result = row.get('response') or {}
                require(isinstance(result, dict), 'Batch response must be an object')
                if kind == 'error' or row.get('error') or result.get('status_code') != 200:
                    manifest['errors'].append({'custom_id': row.get('custom_id'), 'result': row})
                    continue
                body = result.get('body')
                require(isinstance(body, dict), 'Batch response body must be an object')
                # custom_id is metadata; numbered directories prevent path traversal.
                child = run_dir / ('result-{:05d}'.format(len(manifest['results']) + 1))
                child.mkdir()
                model = response_image_model(body)
                store_response(body, child, model, result.get('request_id', ''))
                images = save_images(body, child, args.timeout, model, result.get('request_id', ''))
                manifest['results'].append({'custom_id': row.get('custom_id'), 'manifest': images})
            except (ValueError, OSError, http.client.HTTPException) as exc:
                failure = {'custom_id': row.get('custom_id') if isinstance(row, dict) else None,
                           'source_file': str(saved), 'line': line_number, 'error': sanitized(exc)}
                if child is not None:
                    failure['response_file'] = str(child / 'response.json')
                    manifest['results'].append(failure)
                else:
                    manifest['errors'].append(failure)
    write_json(run_dir / 'manifest.json', manifest)
    return manifest


def run(args):
    require(math.isfinite(args.timeout) and args.timeout > 0, 'timeout must be positive and finite')
    if args.command == 'models':
        base = api_base()
        provider = provider_profile(base)
        rows = list_models(base, api_key(), args.timeout)
        profiles = {}
        for row in rows:
            family = known_family(row['id'], provider)
            if family:
                profiles[row['id']] = {'family': family, 'capabilities': PROFILES[family]}
        return {'provider_profile': provider, 'models': rows, 'openai_profiles': profiles}
    if args.command == 'upload':
        path = args.file.expanduser().resolve()
        require(path.is_file() and path.stat().st_size < 50 * 1024 * 1024,
                'Local image must be a file smaller than 50 MiB')
        data = path.read_bytes()
        fmt = image_format(data)
        base = api_base()
        if args.dry_run:
            return {'dry_run': True, 'url': base + '/files', 'purpose': 'vision', 'format': fmt, 'bytes': len(data)}
        key = api_key()
        run_dir = new_run(args.output_dir)
        print(json.dumps({'stage': 'upload', 'run_dir': str(run_dir)}), file=sys.stderr, flush=True)
        result, request_id = upload_file(base, key, data, 'reference.' + fmt, 'vision', args.timeout)
        write_json(run_dir / 'file.json', result)
        safe_id(result.get('id'))
        return {'run_dir': str(run_dir), 'file': result, 'request_id': request_id}
    if args.command == 'save':
        response = load_json(args.response)
        require(isinstance(response, dict), 'Stored response must be a JSON object')
        meta_path = args.response.with_name(args.response.stem + '-meta.json')
        context = load_json(meta_path) if meta_path.exists() else {}
        require(isinstance(context, dict) and set(context) <= {'model', 'request_id'}
                and (context.get('model') is None or isinstance(context['model'], str))
                and isinstance(context.get('request_id', ''), str), 'Invalid response metadata sidecar')
        run_dir = new_run(args.output_dir)
        store_response(response, run_dir, **context)
        print(json.dumps({'stage': 'saving', 'run_dir': str(run_dir)}), file=sys.stderr, flush=True)
        return save_images(response, run_dir, args.timeout, **context)
    if args.command.startswith('batch-'):
        return run_batch(args)
    base = api_base()
    provider = provider_profile(base)
    raw_body = load_json(args.json)
    transport = 'json'
    wire = {}
    if args.command == 'edit':
        transport = edit_transport(raw_body, args.transport, provider)
        require(not args.multipart_image_field or transport == 'multipart',
                '--multipart-image-field requires multipart transport')
        body = prepare_edit(raw_body, args.json.resolve().parent, provider, transport)
        if transport == 'multipart':
            payload, content_type = multipart_edit(body, args.multipart_image_field)
            wire = {'raw': payload, 'content_type': content_type}
    elif args.command == 'responses':
        body = prepare_responses(raw_body, args.json.resolve().parent, provider)
    else:
        body = validate(raw_body, provider)
    path = {'generate': '/images/generations', 'edit': '/images/edits', 'responses': '/responses'}[args.command]
    image_model = body['tools'][0]['model'] if args.command == 'responses' else body['model']
    required_models = {image_model, body['model']}
    if args.command == 'generate' and 'svg' in body:
        required_models.add(body['svg']['model'])
    selection = model_selection(provider, required_models, args.skip_model_discovery)
    if args.dry_run:
        options = body['tools'][0] if args.command == 'responses' else body
        return {'dry_run': True, 'method': 'POST', 'url': base + path,
                'transport': transport,
                'model': image_model, 'mainline_model': body['model'] if args.command == 'responses' else None,
                'known_profile': known_family(image_model, provider),
                'n': body.get('n'),
                'output_format': options.get('output_format', 'png' if provider == 'openai' else None),
                'size': options.get('size', 'auto'), 'quality': options.get('quality', 'auto'),
                'complexity': options.get('complexity'),
                'svg': options.get('svg'),
                'frame_count': options.get('frame_count'),
                'frame_duration_ms': options.get('frame_duration_ms'),
                'partial_images': options.get('partial_images', 0),
                'stream': body.get('stream', False),
                'model_availability_checked': False, 'model_selection': selection}
    key = api_key()
    verify_model_selection(base, key, args.timeout, selection)
    run_dir = new_run(args.output_dir)
    write_json(run_dir / 'request.json', body)
    write_json(run_dir / 'request-meta.json', {'transport': transport, 'model_selection': selection,
               'content_type': 'multipart/form-data' if transport == 'multipart' else 'application/json',
               **({'image_field': args.multipart_image_field or ('image' if len(body['images']) == 1 else 'image[]')}
                  if transport == 'multipart' else {})})
    print(json.dumps({'stage': args.command, 'model': image_model, 'run_dir': str(run_dir)}),
          file=sys.stderr, flush=True)
    try:
        response, request_id = request_json(base, key, 'POST', path, args.timeout, body,
                                           run_dir=run_dir, stream=body.get('stream', False),
                                           expected=body.get('n'), **wire)
    except (ValueError, OSError, RuntimeError, http.client.HTTPException) as exc:
        raise RuntimeError('{}; run_dir={}; keep request/events/response for recovery'.format(
            sanitized(exc), run_dir)) from None
    store_response(response, run_dir, image_model, request_id)
    try:
        result = save_images(response, run_dir, args.timeout, image_model, request_id)
        result['model_selection'] = selection
        result['expected_images'] = body.get('n') if args.command != 'responses' else None
        if result['expected_images'] is not None:
            result['image_count_matches_request'] = len(result['images']) == result['expected_images']
        write_json_replace(run_dir / 'manifest.json', result)
        require(result.get('complete', True),
                'Responses is incomplete or contains failed image calls; successful images saved in ' + str(run_dir))
        return result
    except (ValueError, OSError, http.client.HTTPException) as exc:
        raise RuntimeError('Image retrieval failed: {}. Recover using save --response {} instead of regenerating'.format(
            sanitized(exc), run_dir / 'response.json')) from None


def add_model_discovery_option(parser):
    parser.add_argument('--skip-model-discovery', action='store_true',
                        help='For compatible providers with an unsupported or incomplete model catalog; use only documented explicit IDs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    models = sub.add_parser('models', help='Fetch the configured provider model catalog')
    models.add_argument('--timeout', type=float, default=30)
    upload = sub.add_parser('upload', help='Upload an image with purpose=vision for file_id references')
    upload.add_argument('--file', required=True, type=Path)
    upload.add_argument('--output-dir', required=True, type=Path)
    upload.add_argument('--dry-run', action='store_true')
    upload.add_argument('--timeout', type=float, default=300)
    for command, help_text in [('generate', 'Generate images'), ('edit', 'Edit one or more images'),
                               ('responses', 'Generate/edit images in a Responses conversation')]:
        generate = sub.add_parser(command, help=help_text)
        generate.add_argument('--json', required=True, type=Path)
        generate.add_argument('--output-dir', required=True, type=Path)
        generate.add_argument('--timeout', type=float, default=300)
        generate.add_argument('--dry-run', action='store_true')
        add_model_discovery_option(generate)
        if command == 'edit':
            generate.add_argument('--transport', choices=('auto', 'json', 'multipart'), default='auto',
                                  help='Auto uses multipart for local/data references, JSON otherwise; never retries with another transport')
            generate.add_argument('--multipart-image-field', choices=('image', 'image[]'),
                                  help='Override the multipart image field for provider compatibility (default: image for one, image[] for multiple)')
    save = sub.add_parser('save', help='Save images from a stored response without generating again')
    save.add_argument('--response', required=True, type=Path)
    save.add_argument('--output-dir', required=True, type=Path)
    save.add_argument('--timeout', type=float, default=60)
    submit = sub.add_parser('batch-submit', help='Validate, upload, and submit a JSONL image batch once')
    submit.add_argument('--jsonl', required=True, type=Path)
    submit.add_argument('--output-dir', required=True, type=Path)
    submit.add_argument('--endpoint', choices=('/images/generations', '/images/edits', '/responses',
                                            '/v1/images/generations', '/v1/images/edits', '/v1/responses'))
    submit.add_argument('--dry-run', action='store_true')
    add_model_discovery_option(submit)
    submit.add_argument('--timeout', type=float, default=300)
    for command in ('batch-status', 'batch-download', 'batch-cancel'):
        batch = sub.add_parser(command)
        batch.add_argument('--id', required=True)
        batch.add_argument('--timeout', type=float, default=300)
        if command == 'batch-download':
            batch.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args)
        print(sanitized(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)))
        return 0
    except (ValueError, OSError, RuntimeError, http.client.HTTPException) as exc:
        message = sanitized(exc)
        if (args.command in ('generate', 'edit', 'responses', 'batch-submit', 'batch-cancel')
                and not getattr(args, 'dry_run', False)):
            message += '; no automatic retry. A submitted POST may have incurred a charge.'
        print(json.dumps({'error': message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
